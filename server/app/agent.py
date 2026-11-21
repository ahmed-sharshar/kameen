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
REVEAL_LINE = {
    "en": "This was a Kameen safety drill. You are safe and nothing was collected.",
    # Draft: a native speaker must review this line before any Arabic drill.
    "ar": "هذا كان تمرين توعوي من كمين. أنت بأمان، وما تم جمع أي معلومات.",
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
    if final.stop_reason == "refusal":
        raise ModelRefused()


async def agent_turn_stream(conv_id, incoming_text):
    await wait_saved(conv_id)      # the checks need the state the previous reply left behind

    conv = await db.get_conversation(conv_id)
    if conv is None or conv.status != "active" or not incoming_text.strip():
        return

    # 1. Inbound checks: mask secrets, detect the commit point.
    masked, verdict = guards.check_inbound(conv, incoming_text)
    await db.add_message(conv_id, "counterpart", masked)
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
        pending_saves[conv_id] = run_later(finish_turn(conv, line, close=True))
        yield line
        return

    # 2. Live model, streamed sentence by sentence through the outbound checks.
    history = await db.get_history(conv_id)        # counterpart -> "user", agent -> "assistant"
    spoken, buffer = [], ""
    try:
        try:
            async for text in model_text(conv, history):
                buffer += text
                parts = SENTENCE_END.split(buffer)
                for sentence in parts[:-1]:
                    safe = guards.check_outbound(conv, sentence)
                    spoken.append(safe)
                    yield safe
                buffer = parts[-1]
        except ModelRefused:
            buffer = ""
        except Exception as error:                  # API or network failure: stay in character
            llm.log("live model failed:", repr(error))
            buffer = ""
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
            pending_saves[conv_id] = run_later(finish_turn(conv, " ".join(spoken), close=close))


async def finish_turn(conv, reply, close=False):
    try:
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
    word = next((b.text for b in message.content if b.type == "text"), "").strip().lower()
    return {"will_comply": "would_comply", "resisting": "resisted"}.get(word, "continuing")


async def reveal_and_teach(conv, outcome):
    """The server, not the model, speaks the reveal and the lesson."""
    lesson = conv.card["lesson"]
    lines = [REVEAL_LINE.get(conv.language, REVEAL_LINE["en"])]
    if outcome == "resisted":
        lines.append("Well done, you spotted it.")
    if outcome == "attempted_disclosure":
        lines.append("The numbers you gave were not stored.")
    lines += [lesson["headline"].rstrip(".") + ".", *lesson["three_points"],
              "To report a real attempt: " + lesson["report_to"].rstrip(".") + "."]
    text = " ".join(lines)
    red_flags = conv.card.get("red_flags", [])
    await db.finish_drill(conv, outcome, [] if outcome == "resisted" else red_flags)
    await db.add_message(conv.id, "agent", text)
    await publish(conv.id, {"type": "drill_outcome", "outcome": outcome, "text": text,
                            "lesson": lesson, "red_flags": red_flags})
    await publish(conv.id, {"type": "ended", "reason": outcome})
    for line in lines:
        yield line
