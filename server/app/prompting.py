"""Builds the prompts. The stable block is cached; the turn note changes every turn."""
import json
from pathlib import Path

PROMPTS = Path(__file__).parent / "prompts"
LANGUAGE_NAMES = {"en": "English", "ar": "Emirati Arabic dialect only (never Modern Standard Arabic)"}

STAGE_GOALS = {
    "decoy": {
        "HOOKED": "Show worry or interest and make it clear you believe the story. Move on once they make a first request.",
        "STALL": "Be slow and a little confused. Ask them to repeat things. Make a small off-topic remark. Waste time politely.",
        "FISH": "Ask one question at a time that makes them reveal a detail: which account or IBAN to send to, "
                "another link because the first does not open, a number to call them back on, their name and department.",
        "CANARY": "Give one piece of your bait, slowly. Give the wrong card number first and correct it when they complain.",
        "WIND_DOWN": "Find an everyday excuse to leave and say you will continue later. Keep the door open.",
    },
    "drill": {
        "PRETEXT": "Establish who you claim to be and why you are contacting them.",
        "PRESSURE": "Apply the card's pressure tactics. Answer doubts the way this scammer would.",
        "ASK": "Explain that verification is needed, then ask the commit question word for word.",
    },
}
MAX_TURNS = {"decoy": 25, "drill": 8}


def _read(name):
    return (PROMPTS / name).read_text(encoding="utf-8")


def _fill(template, values):
    for key, value in values.items():
        template = template.replace("{" + key + "}", str(value))
    return template


def _playbook_text(conv):
    if not conv.playbook:
        return "No playbook yet. Follow the stage goals."
    return json.dumps(conv.playbook, ensure_ascii=False, indent=1)


def _stages_text(mode, card=None):
    goals = dict(STAGE_GOALS[mode])
    if card:
        goals.update(card.get("stage_goals", {}))
    return "\n".join(f"- {stage}: {goal}" for stage, goal in goals.items())


def stable_prompt(conv):
    """Everything that stays the same between turns. Changes once, when the playbook lands."""
    language = LANGUAGE_NAMES.get(conv.language, "English")
    if conv.mode == "decoy":
        persona = {k: v for k, v in conv.persona.items() if k not in ("id", "voice_agent")}
        kit = conv.canary_kit
        return _fill(_read("decoy_system.md"), {
            "persona": json.dumps(persona, ensure_ascii=False, indent=1),
            "card": kit["card"], "card_wrong": kit["card_wrong"], "expiry": kit["expiry"],
            "iban": kit["iban"], "otp": kit["otp"], "language_name": language,
            "stages": _stages_text("decoy"), "playbook": _playbook_text(conv),
        })
    card = {k: v for k, v in conv.card.items()
            if k in ("title", "impersonates", "hook", "pressure_tactics", "ask", "difficulty")}
    return _fill(_read("drill_system.md"), {
        "card": json.dumps(card, ensure_ascii=False, indent=1),
        "commit_question": conv.card["commit_question"], "language_name": language,
        "stages": _stages_text("drill", conv.card), "playbook": _playbook_text(conv),
    })


def turn_note(conv):
    """Sent as a system message after the last incoming message."""
    goals = dict(STAGE_GOALS[conv.mode])
    if conv.card:
        goals.update(conv.card.get("stage_goals", {}))
    lines = [f"Current stage: {conv.stage}. Goal: {goals.get(conv.stage, 'Follow the playbook.')}"]
    if conv.director_note:
        lines.append(f"Objective for this reply: {conv.director_note}")
    lines.append(f"This is your reply {conv.turn_count + 1} of at most {MAX_TURNS[conv.mode]}.")
    if conv.channel == "voice":
        lines.append("This is a phone call: one or two short spoken sentences, numbers as words, no symbols.")
    else:
        lines.append("This is a text chat, not a call: reply as one short message of one or two sentences.")
    return "\n".join(lines)
