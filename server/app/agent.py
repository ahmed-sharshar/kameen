"""One turn. Every channel calls agent_turn_stream; nothing else talks to the live model."""
import asyncio
import re
import time

from . import db, fake, guards, llm
from .director import run_director
from .events import publish
from .extract import run_extractor
from .prompting import stable_prompt, turn_note

SENTENCE_END = re.compile(r"(?<=[.!?؟])\s+")      # includes the Arabic question mark
LIMITS = {"decoy": (25, 300), "drill": (8, 180)}   # turns, seconds of voice
IDLE_SECONDS = {"drill": 15 * 60, "decoy": 2 * 3600}   # a session this quiet is closed
REVEAL_LINE = {
    "en": "This was a Kameen safety drill. You are safe and nothing was collected.",
    # Draft: a native speaker must review this line before any Arabic drill.
    "ar": "هذا كان تمرين توعوي من كمين. أنت بأمان، وما تم جمع أي معلومات.",
}
DRILL_OVER_LINE = "The drill has ended. You can hang up now."
# Arabic lines are drafts: a native Emirati speaker must review them before Arabic drills are used for real.
DRILL_TEXT = {
    "en": {"over": DRILL_OVER_LINE, "well_done": "Well done, you spotted it.",
           "not_stored": "The numbers you gave were not stored.", "report": "To report a real attempt: "},
    "ar": {"over": "انتهى التمرين. تقدر تسكّر الخط الحين.", "well_done": "أحسنت، انتبهت لها.",
           "not_stored": "الأرقام اللي قلتها ما انحفظت.", "report": "للتبليغ عن محاولة حقيقية: "},
}
background = set()
pending_saves = {}


class ModelRefused(Exception):
    pass


def run_later(coro):
    """Start a background job and keep a reference so it is not dropped."""
    task = asyncio.create_task(coro)
    background.add(task)
    task.add_done_callback(background.discard)
    return task


async def settle():
    """Wait for every background job. Used by tests and by scripts."""
    while background:
        await asyncio.gather(*list(background), return_exceptions=True)


async def wait_saved(conv_id):
    """If the previous reply is still being saved, wait for it."""
    saving = pending_saves.get(conv_id)
    if saving is not None:
        await asyncio.shield(saving)


async def model_text(conv, history):
    """Text chunks from the live model, or from the script when no API key is set."""
    if not llm.enabled():
        yield fake.reply(conv)
        return
    llm.trace(history, turn_note(conv))
    async with llm.client().messages.stream(
        model=llm.model("live"),
        max_tokens=300,
        thinking={"type": "disabled"},
        output_config={"effort": "low"},
        system=[{"type": "text", "text": stable_prompt(conv), "cache_control": {"type": "ephemeral"}}],
        messages=history + [{"role": "system", "content": turn_note(conv)}],   # stage and director note
    ) as stream:
        async for text in stream.text_stream:
            yield text
        final = await stream.get_final_message()
    llm.record(llm.model("live"), final.usage)
    if final.stop_reason == "refusal":
        raise ModelRefused()


async def agent_turn_stream(conv_id, incoming_text):
    await wait_saved(conv_id)      # the checks need the state the previous reply left behind

    conv = await db.get_conversation(conv_id)
    if conv is None or conv.status != "active" or not incoming_text.strip():
        return

    # 1. Inbound checks: mask secrets, detect the commit point.
    masked, verdict = guards.check_inbound(conv, incoming_text)
    counterpart_id = await db.add_message(conv_id, "counterpart", masked)
    await publish(conv_id, {"type": "message", "speaker": "counterpart", "text": masked})
    if verdict == "ask_classifier":
        verdict = await classify_commit(conv, masked)

    max_turns, max_seconds = LIMITS[conv.mode]
    over = conv.turn_count >= max_turns or (
        conv.voice_started_at is not None and time.time() - conv.voice_started_at >= max_seconds)

    if conv.mode == "drill" and (over or verdict in guards.REVEAL_VERDICTS):
        outcome = verdict if verdict in guards.REVEAL_VERDICTS else "hesitated"
        async for sentence in reveal_and_teach(conv, outcome):       # fixed text, no model call
            yield sentence
        return
    if conv.mode == "decoy" and over:
        line = conv.persona["goodbye_line"]
        pending_saves[conv_id] = run_later(finish_turn(conv, line, close=True, counterpart_id=counterpart_id))
        yield line
        return

    # 2. Live model, streamed sentence by sentence through the outbound checks.
    history = await db.get_history(conv_id)        # counterpart -> "user", agent -> "assistant"
    spoken, buffer, self_reveal, off_role = [], "", False, False
    try:
        try:
            async for text in model_text(conv, history):
                buffer += text
                parts = SENTENCE_END.split(buffer)
                for sentence in parts[:-1]:
                    if guards.reveals_drill(conv, sentence):
                        self_reveal = True
                        break
                    caught = len(conv.guard_events)
                    safe = guards.check_outbound(conv, sentence)
                    spoken.append(safe)
                    yield safe
                    if "role_leak" in conv.guard_events[caught:]:
                        off_role = True             # the rest of this reply is likely off-role too: drop it
                        break
                if self_reveal or off_role:
                    buffer = ""
                    break
                buffer = parts[-1]
        except ModelRefused:
            buffer = ""
        except Exception as error:                  # API or network failure: stay in character
            llm.log("live model failed:", repr(error))
            buffer = ""
        if not self_reveal and buffer.strip() and guards.reveals_drill(conv, buffer.strip()):
            self_reveal = True
        if self_reveal:
            # The model tried to end the drill itself. The server takes over: what was already
            # said is stored first, then the fixed reveal and lesson follow.
            said, spoken = " ".join(spoken), []
            if said:
                await db.add_message(conv_id, "agent", said)
                await publish(conv_id, {"type": "message", "speaker": "agent", "text": said})
            await publish(conv_id, {"type": "guard", "event": "self_reveal"})
            async for sentence in reveal_and_teach(conv, "hesitated"):
                yield sentence
            return
        if buffer.strip():
            safe = guards.check_outbound(conv, buffer.strip())
            spoken.append(safe)
            yield safe
        if not spoken:                              # refusal, error or empty reply
            line = guards.fallback_line(conv)
            spoken.append(line)
            yield line
    finally:
        # Also runs when the caller interrupts and the request is dropped.
        # No await here: the save runs as its own task.
        if spoken:
            close = conv.mode == "decoy" and conv.stage == "WIND_DOWN"
            pending_saves[conv_id] = run_later(
                finish_turn(conv, " ".join(spoken), close=close, counterpart_id=counterpart_id))


async def voice_turn_stream(conv_id, incoming_text, caller_turns):
    """One voice turn. `caller_turns` is how many caller messages ElevenLabs has in its history.

    ElevenLabs sends a turn again when the caller keeps talking: same number of caller
    messages, newer text, and the reply we gave the first time was never spoken. So a
    re-sent turn replaces the earlier one instead of adding a second.
    """
    await wait_saved(conv_id)
    conv = await db.get_conversation(conv_id)
    if conv is None or conv.voice_started_at is None:
        return
    handled = await db.count_counterpart_since(conv_id, conv.voice_started_at)
    resent = caller_turns <= handled

    if conv.status != "active":
        if conv.mode == "drill" and conv.status == "ended":
            # A drill must never end in silence. If the reveal was given for a turn that
            # ElevenLabs then re-sent, it was not heard: say it again.
            yield (await db.last_agent_message(conv_id)) if resent else DRILL_TEXT.get(
                conv.language, DRILL_TEXT["en"])["over"]
        return

    if resent:
        removed = await db.drop_last_turn(conv_id)
        if removed:
            await publish(conv_id, {"type": "retract", "count": removed})
    async for sentence in agent_turn_stream(conv_id, incoming_text):
        yield sentence


async def finish_turn(conv, reply, close=False, counterpart_id=None):
    try:
        if counterpart_id is not None and not await db.message_exists(counterpart_id):
            return                                 # the turn was replaced; this reply was never heard
        await db.add_message(conv.id, "agent", reply)
        await db.save_turn(conv, close=close)      # turn_count + 1, awaiting_commit, scammer digits
        await publish(conv.id, {"type": "message", "speaker": "agent", "text": reply})
        for event in conv.guard_events:
            await publish(conv.id, {"type": "guard", "event": event})
    finally:
        if pending_saves.get(conv.id) is asyncio.current_task():
            del pending_saves[conv.id]
    if close:
        await publish(conv.id, {"type": "ended", "reason": "wind_down"})
    run_later(run_extractor(conv.id))                           # patterns + Haiku -> intel cards
    if not close:
        run_later(run_director(conv.id, conv.turn_count + 1))   # Sonnet -> stage and next objective


async def classify_commit(conv, masked_text):
    """The one model call allowed before a reply. Runs only after the commit question."""
    if not llm.enabled():
        return "continuing"
    llm.trace(masked_text)
    try:
        message = await llm.client().messages.create(
            model=llm.model("live"),
            max_tokens=16,
            thinking={"type": "disabled"},
            output_config={"effort": "low"},
            system="A trainee in a security drill was asked: '" + conv.card["commit_question"] + "'. "
                   "Classify their reply. Answer with one word: will_comply, hesitating or resisting.",
            messages=[{"role": "user", "content": masked_text}],
        )
    except Exception as error:
        llm.log("commit classifier failed:", repr(error))
        return "continuing"
    llm.record(llm.model("live"), message.usage)
    word = next((b.text for b in message.content if b.type == "text"), "").strip().lower()
    return {"will_comply": "would_comply", "resisting": "resisted"}.get(word, "continuing")


async def close_idle(idle=None):
    """Closes sessions nobody is in any more. An abandoned drill is still revealed on the record,
    so no drill is ever left open. Telegram chats are left alone: scammers there reply slowly."""
    idle = idle or IDLE_SECONDS
    closed = 0
    for conv_id, mode, channel, quiet in await db.idle_conversations():
        if channel == "telegram" or quiet < idle[mode] or conv_id in pending_saves:
            continue
        if mode == "drill":
            conv = await db.get_conversation(conv_id)
            async for _line in reveal_and_teach(conv, "stopped"):
                pass
        else:
            await db.end_conversation(conv_id)
            await publish(conv_id, {"type": "ended", "reason": "idle"})
        closed += 1
    return closed


async def reveal_and_teach(conv, outcome):
    """The server, not the model, speaks the reveal and the lesson."""
    lesson = conv.card["lesson"]
    words = DRILL_TEXT.get(conv.language, DRILL_TEXT["en"])
    lines = [REVEAL_LINE.get(conv.language, REVEAL_LINE["en"])]
    if outcome == "resisted":
        lines.append(words["well_done"])
    if outcome == "attempted_disclosure":
        lines.append(words["not_stored"])
    lines += [lesson["headline"].rstrip(".") + ".", *lesson["three_points"],
              words["report"] + lesson["report_to"].rstrip(".") + "."]
    text = " ".join(lines)
    red_flags = conv.card.get("red_flags", [])
    await db.finish_drill(conv, outcome, [] if outcome == "resisted" else red_flags)
    await db.add_message(conv.id, "agent", text)
    await publish(conv.id, {"type": "drill_outcome", "outcome": outcome, "text": text,
                            "lesson": lesson, "red_flags": red_flags})
    await publish(conv.id, {"type": "ended", "reason": outcome})
    for line in lines:
        yield line
