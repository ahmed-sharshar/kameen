"""Tables and queries. SQLite locally, Postgres on Render; the code is the same."""
import os
import time
import uuid
from types import SimpleNamespace

from sqlalchemy import JSON, Boolean, Float, Integer, String, Text, func, select, update
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
        id=row.id, mode=row.mode, channel=row.channel, language=row.language,
        persona_id=row.persona_id, scenario_id=row.scenario_id, enrolment_id=row.enrolment_id,
        stage=row.stage, status=row.status, turn_count=row.turn_count,
        awaiting_commit=row.awaiting_commit, voice_agent=row.voice_agent,
        opening_line=row.opening_line, director_note=row.director_note or "",
        playbook=row.playbook, canary_kit=kit, started_at=row.started_at,
        voice_started_at=row.voice_started_at,
        persona=cards.persona(row.persona_id) if row.persona_id else None,
        card=cards.scenario(row.scenario_id) if row.scenario_id else None,
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
    async with Session() as s:
        s.add(Message(conversation_id=conv_id, speaker=speaker, text=text, created_at=time.time()))
        await s.commit()


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
    async with Session() as s:
        rows = (await s.execute(select(DrillResult))).scalars().all()
    return [{"scenario_id": r.scenario_id, "group": r.group_name, "outcome": r.outcome} for r in rows]


# ---- enrolments ------------------------------------------------------------

async def add_enrolment(person, group_name, handle, enrolled_by, channels, days=30):
    row = Enrolment(id=str(uuid.uuid4()), person=person[:80], handle=handle[:120], group_name=group_name[:80],
                    enrolled_by=enrolled_by, consent_at=time.time(), channels=channels,
                    expires_at=time.time() + days * 86400)
    async with Session() as s:
        s.add(row)
        await s.commit()
    return row.id


async def get_enrolment(enrolment_id):
    async with Session() as s:
        row = await s.get(Enrolment, enrolment_id)
    if not row:
        return None
    return SimpleNamespace(id=row.id, person=row.person, group_name=row.group_name, channels=row.channels,
                           expires_at=row.expires_at, last_drill_at=row.last_drill_at)


# ---- small key/value store (test metrics) ----------------------------------

async def put_value(key, value):
    async with Session() as s:
        row = await s.get(KeyValue, key)
        if row:
            row.value = value
        else:
            s.add(KeyValue(key=key, value=value))
        await s.commit()


async def get_value(key):
    async with Session() as s:
        row = await s.get(KeyValue, key)
    return row.value if row else None
