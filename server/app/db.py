"""Tables and queries. SQLite locally, Postgres on Render; the code is the same."""
import os
import time
import uuid
from types import SimpleNamespace

from sqlalchemy import JSON, Boolean, Float, Integer, String, Text, delete, func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from . import canaries, cards


def _url():
    url = os.environ.get("DATABASE_URL") or "sqlite+aiosqlite:///./kameen.db"
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


URL = _url()
engine = create_async_engine(URL, pool_pre_ping=True,
                             connect_args={"timeout": 30} if URL.startswith("sqlite") else {})
Session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mode: Mapped[str] = mapped_column(String(10))
    channel: Mapped[str] = mapped_column(String(12))
    language: Mapped[str] = mapped_column(String(8), default="en")
    persona_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scenario_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    enrolment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)   # Telegram chat id
    stage: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(10), default="active")
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    awaiting_commit: Mapped[bool] = mapped_column(Boolean, default=False)
    voice_agent: Mapped[str] = mapped_column(String(20), default="english")
    opening_line: Mapped[str] = mapped_column(Text, default="")
    director_note: Mapped[str] = mapped_column(Text, default="")
    playbook: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    canary_kit: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    counterpart_digits: Mapped[list] = mapped_column(JSON, default=list)   # Decoy: numbers the scammer said
    agent_digits: Mapped[list] = mapped_column(JSON, default=list)         # Drill: numbers the agent said
    risk_flags: Mapped[list] = mapped_column(JSON, default=list)
    rating: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[float] = mapped_column(Float)
    voice_started_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    ended_at: Mapped[float | None] = mapped_column(Float, nullable=True)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(String(36), index=True)
    speaker: Mapped[str] = mapped_column(String(12))      # counterpart, agent, marker
    text: Mapped[str] = mapped_column(Text)               # masked in Drill mode
    created_at: Mapped[float] = mapped_column(Float)


class Intel(Base):
    __tablename__ = "intel"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(String(36), index=True)
    type: Mapped[str] = mapped_column(String(16))
    value: Mapped[str] = mapped_column(Text)
    normalised_value: Mapped[str] = mapped_column(String(128), index=True)
    quote: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String(12))       # regex or extractor
    created_at: Mapped[float] = mapped_column(Float)


class Canary(Base):
    __tablename__ = "canaries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(12))
    value: Mapped[str] = mapped_column(String(64))
    issued_at: Mapped[float] = mapped_column(Float)
    triggered_at: Mapped[float | None] = mapped_column(Float, nullable=True)


class Enrolment(Base):
    __tablename__ = "enrolments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    person: Mapped[str] = mapped_column(String(80))
    handle: Mapped[str] = mapped_column(String(120), default="")
    group_name: Mapped[str] = mapped_column(String(80), default="")
    enrolled_by: Mapped[str] = mapped_column(String(20))  # self or operator
    consent_at: Mapped[float] = mapped_column(Float)
    channels: Mapped[list] = mapped_column(JSON, default=list)
    expires_at: Mapped[float] = mapped_column(Float)
    last_drill_at: Mapped[float | None] = mapped_column(Float, nullable=True)


class DrillResult(Base):
    __tablename__ = "drill_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(String(36), index=True)
    enrolment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    scenario_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    group_name: Mapped[str] = mapped_column(String(80), default="")
    outcome: Mapped[str] = mapped_column(String(24))
    flags_missed: Mapped[list] = mapped_column(JSON, default=list)
    turns: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[float] = mapped_column(Float)


class Event(Base):
    """Append-only audit log."""
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(24))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[float] = mapped_column(Float)


class Invite(Base):
    """An organiser's invitation to a surprise drill: one link for a whole group."""
    __tablename__ = "invites"
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    group_name: Mapped[str] = mapped_column(String(80))
    scenario_id: Mapped[str | None] = mapped_column(String(64), nullable=True)   # None: picked at random per person
    language: Mapped[str] = mapped_column(String(8), default="en")
    window_minutes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[float] = mapped_column(Float)


class ScheduledDrill(Base):
    """One person's drill, waiting for its unannounced moment."""
    __tablename__ = "scheduled_drills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invite_code: Mapped[str] = mapped_column(String(16), index=True)
    enrolment_id: Mapped[str] = mapped_column(String(36))
    chat: Mapped[str] = mapped_column(String(40), index=True)          # "tg:<chat id>"
    scenario_id: Mapped[str] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(8), default="en")
    due_at: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(12), default="waiting")  # waiting, sent, cancelled, refused
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class PhishCampaign(Base):
    """One security-awareness email campaign an organiser runs against a group they authorise."""
    __tablename__ = "phish_campaigns"
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    group_name: Mapped[str] = mapped_column(String(80))
    scenario_id: Mapped[str | None] = mapped_column(String(64), nullable=True)   # None: a different one per person
    language: Mapped[str] = mapped_column(String(8), default="en")
    authorised_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[float] = mapped_column(Float)


class PhishTarget(Base):
    """One recipient of a simulated phishing email. The token is the only thing the link carries."""
    __tablename__ = "phish_targets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_code: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(200))
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    scenario_id: Mapped[str] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(8), default="en")
    status: Mapped[str] = mapped_column(String(12), default="queued")   # queued, sent, failed, clicked
    error: Mapped[str] = mapped_column(String(200), default="")
    sent_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    clicked_at: Mapped[float | None] = mapped_column(Float, nullable=True)


class Case(Base):
    """A SIMULATED police-side case, opened when a drill shows a person was about to hand over a secret
    or a phishing link is clicked. Synthetic only: never filed to TAMM, UAE Pass or Aman."""
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_ref: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    person: Mapped[str] = mapped_column(String(80))
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(24), nullable=True)
    channel: Mapped[str] = mapped_column(String(12))                 # voice, web, telegram, email
    scam_type: Mapped[str] = mapped_column(String(120))
    scenario_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome: Mapped[str] = mapped_column(String(24))                 # the drill outcome, or "clicked"
    source: Mapped[str] = mapped_column(String(12))                  # drill or phishing
    group_name: Mapped[str] = mapped_column(String(80), default="")
    emirates_id: Mapped[str] = mapped_column(String(24), default="")  # mock UAE Pass identity
    status: Mapped[str] = mapped_column(String(16), default="Open")
    sms_text: Mapped[str] = mapped_column(Text, default="")           # the simulated follow-up SMS
    created_at: Mapped[float] = mapped_column(Float)


class KeyValue(Base):
    __tablename__ = "kv"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)


async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ---- conversations -------------------------------------------------------

def _state(row):
    """A plain object for one turn. Checks may change it; save_turn writes it back."""
    kit = row.canary_kit or {}
    return SimpleNamespace(
        id=row.id, mode=row.mode, channel=row.channel, language=row.language, external_id=row.external_id,
        persona_id=row.persona_id, scenario_id=row.scenario_id, enrolment_id=row.enrolment_id,
        stage=row.stage, status=row.status, turn_count=row.turn_count,
        awaiting_commit=row.awaiting_commit, voice_agent=row.voice_agent,
        opening_line=row.opening_line, director_note=row.director_note or "",
        playbook=row.playbook, canary_kit=kit, started_at=row.started_at,
        voice_started_at=row.voice_started_at,
        persona=cards.persona(row.persona_id) if row.persona_id else None,
        card=cards.scenario(row.scenario_id, row.language if row.mode == "drill" else None)
        if row.scenario_id else None,
        canary_digits=canaries.kit_digits(kit),
        counterpart_digits=list(row.counterpart_digits or []),
        agent_digits=list(row.agent_digits or []),
        risk_flags=list(row.risk_flags or []),
        guard_events=[],
    )


async def create_conversation(**fields):
    row = Conversation(id=str(uuid.uuid4()), started_at=time.time(), **fields)
    async with Session() as s:
        s.add(row)
        for kind in ("card", "iban", "otp"):
            if row.canary_kit:
                s.add(Canary(conversation_id=row.id, kind=kind, value=row.canary_kit[kind], issued_at=time.time()))
        await s.commit()
    return _state(row)


async def get_conversation(conv_id):
    async with Session() as s:
        row = await s.get(Conversation, conv_id)
    return _state(row) if row else None


async def find_by_external(external_id):
    async with Session() as s:
        row = (await s.execute(
            select(Conversation).where(Conversation.external_id == external_id, Conversation.status == "active")
            .order_by(Conversation.started_at.desc()))).scalars().first()
    return _state(row) if row else None


async def _patch(conv_id, **values):
    async with Session() as s:
        await s.execute(update(Conversation).where(Conversation.id == conv_id).values(**values))
        await s.commit()


async def save_turn(conv, close=False):
    values = {"turn_count": conv.turn_count + 1, "awaiting_commit": conv.awaiting_commit,
              "counterpart_digits": conv.counterpart_digits, "agent_digits": conv.agent_digits}
    if close:
        values.update(status="ended", ended_at=time.time())
    await _patch(conv.id, **values)


async def set_director(conv_id, turn, stage, note, flags):
    """Writes only if the conversation is still on the turn the director looked at."""
    async with Session() as s:
        result = await s.execute(
            update(Conversation)
            .where(Conversation.id == conv_id, Conversation.turn_count == turn, Conversation.status == "active")
            .values(stage=stage, director_note=note, risk_flags=flags))
        await s.commit()
    return result.rowcount == 1


async def set_playbook(conv_id, playbook):
    await _patch(conv_id, playbook=playbook)


async def mark_voice(conv_id):
    await _patch(conv_id, channel="voice", voice_started_at=time.time())


async def end_conversation(conv_id, status="ended"):
    await _patch(conv_id, status=status, ended_at=time.time())


async def idle_conversations():
    """Every open conversation with how long it has been quiet: (id, mode, channel, seconds)."""
    now = time.time()
    async with Session() as s:
        rows = (await s.execute(
            select(Conversation.id, Conversation.mode, Conversation.channel, Conversation.started_at,
                   func.max(Message.created_at))
            .outerjoin(Message, Message.conversation_id == Conversation.id)
            .where(Conversation.status == "active")
            .group_by(Conversation.id, Conversation.mode, Conversation.channel, Conversation.started_at))).all()
    return [(conv_id, mode, channel, now - max(started, latest or 0))
            for conv_id, mode, channel, started, latest in rows]


async def set_rating(conv_id, text):
    await _patch(conv_id, rating=text[:500])


async def list_conversations(limit=100):
    async with Session() as s:
        rows = (await s.execute(
            select(Conversation).order_by(Conversation.started_at.desc()).limit(limit))).scalars().all()
        counts = dict((await s.execute(
            select(Intel.conversation_id, func.count()).group_by(Intel.conversation_id))).all())
    return [{"id": r.id, "mode": r.mode, "channel": r.channel, "persona_id": r.persona_id,
             "scenario_id": r.scenario_id, "stage": r.stage, "status": r.status,
             "turn_count": r.turn_count, "started_at": r.started_at,
             "intel_count": counts.get(r.id, 0)} for r in rows]


# ---- messages ------------------------------------------------------------

async def add_message(conv_id, speaker, text):
    row = Message(conversation_id=conv_id, speaker=speaker, text=text, created_at=time.time())
    async with Session() as s:
        s.add(row)
        await s.commit()
    return row.id


async def message_exists(message_id):
    async with Session() as s:
        return (await s.execute(select(Message.id).where(Message.id == message_id))).first() is not None


async def count_counterpart_since(conv_id, since):
    """How many turns the other side has taken since the voice call opened."""
    async with Session() as s:
        return (await s.execute(select(func.count()).select_from(Message).where(
            Message.conversation_id == conv_id, Message.speaker == "counterpart",
            Message.created_at >= since))).scalar_one()


async def last_agent_message(conv_id):
    async with Session() as s:
        row = (await s.execute(select(Message).where(
            Message.conversation_id == conv_id, Message.speaker == "agent")
            .order_by(Message.id.desc()))).scalars().first()
    return row.text if row else ""


async def drop_last_turn(conv_id):
    """Removes the other side's last message and any reply to it. Returns how many messages went."""
    async with Session() as s:
        last = (await s.execute(select(Message).where(
            Message.conversation_id == conv_id, Message.speaker == "counterpart")
            .order_by(Message.id.desc()))).scalars().first()
        if last is None:
            return 0
        doomed = (await s.execute(select(Message).where(
            Message.conversation_id == conv_id, Message.id >= last.id))).scalars().all()
        had_reply = any(m.speaker == "agent" for m in doomed)
        await s.execute(delete(Message).where(Message.conversation_id == conv_id, Message.id >= last.id))
        if had_reply:                                   # that reply had been counted as a turn
            conv = await s.get(Conversation, conv_id)
            conv.turn_count = max(0, conv.turn_count - 1)
        await s.commit()
    return len(doomed)


async def get_messages(conv_id):
    async with Session() as s:
        rows = (await s.execute(
            select(Message).where(Message.conversation_id == conv_id).order_by(Message.id))).scalars().all()
    return [{"speaker": r.speaker, "text": r.text, "created_at": r.created_at} for r in rows]


async def get_history(conv_id):
    """Messages in the shape the Anthropic API expects. The first one is always a user message."""
    history = []
    for m in await get_messages(conv_id):
        role = "assistant" if m["speaker"] == "agent" else "user"
        if history and history[-1]["role"] == role:
            history[-1]["content"] += "\n" + m["text"]
        else:
            history.append({"role": role, "content": m["text"]})
    return history


# ---- intel, events, drills -------------------------------------------------

async def add_intel(conv_id, item):
    """Returns True if this value is new for the conversation."""
    async with Session() as s:
        seen = (await s.execute(select(Intel.id).where(
            Intel.conversation_id == conv_id, Intel.normalised_value == item["normalised_value"]))).first()
        if seen:
            return False
        s.add(Intel(conversation_id=conv_id, created_at=time.time(), **item))
        await s.commit()
    return True


async def list_intel(conv_id=None):
    async with Session() as s:
        query = select(Intel).order_by(Intel.id)
        if conv_id:
            query = query.where(Intel.conversation_id == conv_id)
        rows = (await s.execute(query)).scalars().all()
    return [{"conversation_id": r.conversation_id, "type": r.type, "value": r.value,
             "normalised_value": r.normalised_value, "quote": r.quote,
             "confidence": r.confidence, "source": r.source} for r in rows]


async def add_event(conv_id, event):
    async with Session() as s:
        s.add(Event(conversation_id=conv_id, kind=event.get("type", "event"), payload=event, created_at=time.time()))
        await s.commit()


async def list_canaries(conv_id):
    async with Session() as s:
        rows = (await s.execute(select(Canary).where(Canary.conversation_id == conv_id))).scalars().all()
    return [{"kind": r.kind, "value": r.value} for r in rows]


async def finish_drill(conv, outcome, flags_missed):
    now = time.time()
    async with Session() as s:
        group = ""
        if conv.enrolment_id:
            enrolment = await s.get(Enrolment, conv.enrolment_id)
            if enrolment:
                enrolment.last_drill_at = now
                group = enrolment.group_name
        s.add(DrillResult(conversation_id=conv.id, enrolment_id=conv.enrolment_id, scenario_id=conv.scenario_id,
                          group_name=group, outcome=outcome, flags_missed=flags_missed,
                          turns=conv.turn_count, created_at=now))
        await s.execute(update(Conversation).where(Conversation.id == conv.id)
                        .values(stage="LESSON", status="ended", ended_at=now))
        await s.commit()


async def get_drill_result(conv_id):
    async with Session() as s:
        row = (await s.execute(select(DrillResult).where(DrillResult.conversation_id == conv_id))).scalars().first()
    return {"outcome": row.outcome, "turns": row.turns} if row else None


async def list_drill_results():
    """Each drill result with the channel it ran on (from its conversation) and the flags missed."""
    async with Session() as s:
        rows = (await s.execute(
            select(DrillResult, Conversation.channel).join(
                Conversation, Conversation.id == DrillResult.conversation_id, isouter=True))).all()
    return [{"scenario_id": r.scenario_id, "group": r.group_name, "outcome": r.outcome,
             "channel": channel or "web", "flags_missed": list(r.flags_missed or []),
             "turns": r.turns, "created_at": r.created_at} for r, channel in rows]


# ---- enrolments ------------------------------------------------------------

async def add_enrolment(person, group_name, handle, enrolled_by, channels, days=30):
    row = Enrolment(id=str(uuid.uuid4()), person=person[:80], handle=handle[:120], group_name=group_name[:80],
                    enrolled_by=enrolled_by, consent_at=time.time(), channels=channels,
                    expires_at=time.time() + days * 86400)
    async with Session() as s:
        s.add(row)
        await s.commit()
    return row.id


async def find_enrolment(handle, channel):
    """The person's current consent for a channel, found by their handle. None if they have none."""
    async with Session() as s:
        rows = (await s.execute(select(Enrolment).where(Enrolment.handle == handle, Enrolment.expires_at > time.time())
                                .order_by(Enrolment.consent_at.desc()))).scalars().all()
    return next((row.id for row in rows if channel in row.channels), None)


async def withdraw(handle):
    """Ends every consent this handle gave and cancels drills still waiting. Returns how many consents ended."""
    now = time.time()
    async with Session() as s:
        ended = (await s.execute(update(Enrolment).where(Enrolment.handle == handle, Enrolment.expires_at > now)
                                 .values(expires_at=now))).rowcount
        await s.execute(update(ScheduledDrill).where(ScheduledDrill.chat == handle, ScheduledDrill.status == "waiting")
                        .values(status="cancelled"))
        await s.commit()
    return ended


# ---- phishing-awareness email campaigns ------------------------------------

async def add_campaign(code, group_name, scenario_id, language, authorised_by, recipients):
    """One campaign and its queued recipients. `recipients` is a list of (name, email, token, scenario_id)."""
    async with Session() as s:
        s.add(PhishCampaign(code=code, group_name=group_name[:80], scenario_id=scenario_id, language=language,
                            authorised_by=authorised_by[:120], created_at=time.time()))
        for name, email, token, scn in recipients:
            s.add(PhishTarget(campaign_code=code, name=name[:80], email=email[:200], token=token,
                              scenario_id=scn, language=language))
        await s.commit()


async def queued_targets():
    async with Session() as s:
        rows = (await s.execute(select(PhishTarget).where(PhishTarget.status == "queued"))).scalars().all()
    return [SimpleNamespace(id=r.id, name=r.name, email=r.email, token=r.token, scenario_id=r.scenario_id,
                            language=r.language) for r in rows]


async def mark_target(target_id, status, error=""):
    values = {"status": status, "error": error[:200]}
    if status == "sent":
        values["sent_at"] = time.time()
    async with Session() as s:
        await s.execute(update(PhishTarget).where(PhishTarget.id == target_id).values(**values))
        await s.commit()


async def record_click(token):
    """Marks the first click on a token and returns the target, or None for an unknown token."""
    async with Session() as s:
        row = (await s.execute(select(PhishTarget).where(PhishTarget.token == token))).scalars().first()
        if row is None:
            return None
        first = row.clicked_at is None
        if first:
            row.clicked_at = time.time()
            if row.status != "failed":
                row.status = "clicked"
            await s.commit()
        return SimpleNamespace(scenario_id=row.scenario_id, language=row.language, name=row.name,
                               email=row.email, campaign_code=row.campaign_code, first_click=first)


# ---- simulated police cases --------------------------------------------------

async def add_case(case_ref, person, email, phone, channel, scam_type, scenario_id, outcome, source,
                   group_name, emirates_id, sms_text):
    async with Session() as s:
        s.add(Case(case_ref=case_ref, person=(person or "Unknown")[:80], email=(email or None),
                   phone=(phone or None), channel=channel, scam_type=(scam_type or "")[:120],
                   scenario_id=scenario_id, outcome=outcome, source=source, group_name=(group_name or "")[:80],
                   emirates_id=emirates_id, status="Open", sms_text=sms_text, created_at=time.time()))
        await s.commit()
    return case_ref


async def count_cases():
    async with Session() as s:
        return (await s.execute(select(func.count()).select_from(Case))).scalar_one()


async def get_case(case_ref):
    async with Session() as s:
        row = (await s.execute(select(Case).where(Case.case_ref == case_ref))).scalars().first()
    if row is None:
        return None
    return {"case_ref": row.case_ref, "person": row.person, "email": row.email, "phone": row.phone,
            "channel": row.channel, "scam_type": row.scam_type, "scenario_id": row.scenario_id,
            "outcome": row.outcome, "group_name": row.group_name, "emirates_id": row.emirates_id,
            "status": row.status, "sms_text": row.sms_text}


async def set_case_status(case_ref, status):
    async with Session() as s:
        await s.execute(update(Case).where(Case.case_ref == case_ref).values(status=status))
        await s.commit()


async def set_case_emailed(case_ref, to):
    """Records that the case details were emailed, and to whom (kept in sms_text for display)."""
    async with Session() as s:
        await s.execute(update(Case).where(Case.case_ref == case_ref).values(status="Emailed", sms_text=to))
        await s.commit()


async def list_cases(limit=200):
    async with Session() as s:
        rows = (await s.execute(select(Case).order_by(Case.created_at.desc()).limit(limit))).scalars().all()
    return [{"case_ref": r.case_ref, "person": r.person, "email": r.email, "phone": r.phone,
             "channel": r.channel, "scam_type": r.scam_type, "outcome": r.outcome, "source": r.source,
             "group_name": r.group_name, "emirates_id": r.emirates_id, "status": r.status,
             "sms_text": r.sms_text, "created_at": r.created_at} for r in rows]


async def list_campaigns():
    """Every campaign with its recipients: who was sent to, and who clicked. Behind the access code."""
    async with Session() as s:
        campaigns = (await s.execute(select(PhishCampaign).order_by(PhishCampaign.created_at.desc()))).scalars().all()
        targets = (await s.execute(select(PhishTarget))).scalars().all()
    by_code = {}
    for t in targets:
        by_code.setdefault(t.campaign_code, []).append(t)
    rows = []
    for c in campaigns:
        mine = sorted(by_code.get(c.code, []), key=lambda t: (t.clicked_at is None, t.name.lower()))
        rows.append({
            "code": c.code, "group_name": c.group_name, "scenario_id": c.scenario_id, "language": c.language,
            "authorised_by": c.authorised_by, "created_at": c.created_at, "recipients": len(mine),
            "sent": sum(t.status in ("sent", "clicked") for t in mine),
            "failed": sum(t.status == "failed" for t in mine),
            "clicked": sum(t.clicked_at is not None for t in mine),
            "people": [{"name": t.name, "email": t.email, "status": t.status,
                        "sent_at": t.sent_at, "clicked_at": t.clicked_at, "error": t.error} for t in mine],
        })
    return rows


# ---- surprise drills -------------------------------------------------------

async def add_invite(code, group_name, scenario_id, language, window_minutes):
    async with Session() as s:
        s.add(Invite(code=code, group_name=group_name[:80], scenario_id=scenario_id, language=language,
                     window_minutes=window_minutes, created_at=time.time()))
        await s.commit()


async def get_invite(code, valid_days=14):
    async with Session() as s:
        row = await s.get(Invite, code)
    if row is None or row.created_at < time.time() - valid_days * 86400:
        return None
    return SimpleNamespace(code=row.code, group_name=row.group_name, scenario_id=row.scenario_id,
                           language=row.language, window_minutes=row.window_minutes)


async def list_invites():
    """Each invite with counts only: how many joined, are waiting, were sent, and finished."""
    async with Session() as s:
        invites = (await s.execute(select(Invite).order_by(Invite.created_at.desc()))).scalars().all()
        drills = (await s.execute(select(ScheduledDrill))).scalars().all()
        finished = set((await s.execute(select(DrillResult.conversation_id))).scalars().all())
    rows = []
    for invite in invites:
        mine = [d for d in drills if d.invite_code == invite.code and d.status != "cancelled"]
        rows.append({"code": invite.code, "group_name": invite.group_name, "scenario_id": invite.scenario_id,
                     "language": invite.language, "window_minutes": invite.window_minutes,
                     "created_at": invite.created_at, "joined": len(mine),
                     "waiting": sum(d.status == "waiting" for d in mine),
                     "sent": sum(d.status == "sent" for d in mine),
                     "finished": sum(d.conversation_id in finished for d in mine)})
    return rows


async def add_scheduled(invite_code, enrolment_id, chat, scenario_id, language, due_at):
    async with Session() as s:
        s.add(ScheduledDrill(invite_code=invite_code, enrolment_id=enrolment_id, chat=chat, scenario_id=scenario_id,
                             language=language, due_at=due_at))
        await s.commit()


async def due_drills():
    async with Session() as s:
        rows = (await s.execute(select(ScheduledDrill).where(
            ScheduledDrill.status == "waiting", ScheduledDrill.due_at <= time.time()))).scalars().all()
    return [SimpleNamespace(id=r.id, enrolment_id=r.enrolment_id, chat=r.chat, scenario_id=r.scenario_id,
                            language=r.language) for r in rows]


async def mark_scheduled(drill_id, status, conversation_id=None):
    async with Session() as s:
        await s.execute(update(ScheduledDrill).where(ScheduledDrill.id == drill_id)
                        .values(status=status, conversation_id=conversation_id))
        await s.commit()


async def chat_language(chat):
    """The language of this chat's latest drill, so later messages match it."""
    async with Session() as s:
        row = (await s.execute(select(ScheduledDrill).where(ScheduledDrill.chat == chat)
                               .order_by(ScheduledDrill.id.desc()))).scalars().first()
    return row.language if row else "en"


async def get_enrolment(enrolment_id):
    if not enrolment_id:
        return None
    async with Session() as s:
        row = await s.get(Enrolment, enrolment_id)
    if not row:
        return None
    return SimpleNamespace(id=row.id, person=row.person, handle=row.handle, group_name=row.group_name,
                           channels=row.channels, expires_at=row.expires_at, last_drill_at=row.last_drill_at)


# ---- small key/value store (test metrics) ----------------------------------

async def put_value(key, value):
    async with Session() as s:
        row = await s.get(KeyValue, key)
        if row:
            row.value = value
        else:
            s.add(KeyValue(key=key, value=value))
        await s.commit()


async def drop_value(key):
    async with Session() as s:
        await s.execute(delete(KeyValue).where(KeyValue.key == key))
        await s.commit()


async def get_value(key):
    async with Session() as s:
        row = await s.get(KeyValue, key)
    return row.value if row else None
