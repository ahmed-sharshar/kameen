"""The two slow models. Neither is ever in the reply path."""
import json

from . import db, guards, llm
from .events import publish
from .prompting import PROMPTS, STAGE_GOALS

DECOY_ORDER = ["HOOKED", "STALL", "FISH", "CANARY", "WIND_DOWN"]
DRILL_ORDER = ["PRETEXT", "PRESSURE", "ASK"]          # the rest is set by code only
RISK_FLAGS = ["distress", "suspects_bot", "abusive", "wind_down"]

PLAYBOOK_SCHEMA = {
    "type": "object",
    "properties": {"stages": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "stage": {"type": "string"},
            "goal": {"type": "string"},
            "example_lines": {"type": "array", "items": {"type": "string"}},
            "if_they_say": {"type": "array", "items": {
                "type": "object",
                "properties": {"they": {"type": "string"}, "you": {"type": "string"}},
                "required": ["they", "you"], "additionalProperties": False}},
            "exit_when": {"type": "string"},
        },
        "required": ["stage", "goal", "example_lines", "if_they_say", "exit_when"],
        "additionalProperties": False}}},
    "required": ["stages"], "additionalProperties": False,
}


def director_schema(mode):
    stages = DECOY_ORDER if mode == "decoy" else DRILL_ORDER
    return {
        "type": "object",
        "properties": {
            "stage": {"type": "string", "enum": stages},
            "next_objective": {"type": "string"},
            "risk_flags": {"type": "array", "items": {"type": "string", "enum": RISK_FLAGS}},
        },
        "required": ["stage", "next_objective", "risk_flags"], "additionalProperties": False,
    }


def legal_move(mode, current, proposed):
    """Decoy: stay, one step forward, or WIND_DOWN. Drill: stay or one step forward, up to ASK."""
    order = DECOY_ORDER if mode == "decoy" else DRILL_ORDER
    if current not in order or proposed not in order:
        return False
    step = order.index(proposed) - order.index(current)
    return step in (0, 1) or (mode == "decoy" and proposed == "WIND_DOWN")


async def make_playbook(conv_id):
    """Opus 5.5, once per session. The first turns run on the card's stage goals until this lands."""
    if not llm.enabled():
        return
    conv = await db.get_conversation(conv_id)
    if conv is None:
        return
    if conv.mode == "decoy":
        subject = {"mode": "decoy", "persona": conv.persona, "scenario_hint": conv.card}
    else:
        subject = {"mode": "drill", "scenario_card": conv.card}
    user = json.dumps({**subject, "stages": STAGE_GOALS[conv.mode], "language": conv.language}, ensure_ascii=False)
    result = await llm.json_call("playbook", (PROMPTS / "playbook.md").read_text(encoding="utf-8"),
                                 user, PLAYBOOK_SCHEMA, max_tokens=8000, effort="medium")
    if not result:
        return
    playbook = {}
    for stage in result["stages"]:
        if stage["stage"] not in STAGE_GOALS[conv.mode]:
            continue
        if conv.mode == "drill":
            # Fallback lines are spoken without a model, so they must already be safe.
            stage["example_lines"] = [line for line in stage["example_lines"]
                                      if not guards.ASKS_FOR_SECRET.search(line)
                                      and not guards.gives_payment_detail(line)]
        playbook[stage["stage"]] = stage
    if conv.mode == "drill" and "ASK" in playbook:
        playbook["ASK"]["example_lines"] = [conv.card["commit_question"]]
    await db.set_playbook(conv_id, playbook)


async def run_director(conv_id, turn):
    """Sonnet 5.5, after each reply. Its result is dropped if a newer turn has started."""
    if not llm.enabled():
        return
    conv = await db.get_conversation(conv_id)
    if conv is None or conv.status != "active" or conv.turn_count != turn:
        return
    them, us = ("SCAMMER", "DECOY") if conv.mode == "decoy" else ("TRAINEE", "DRILL AGENT")
    transcript = "\n".join(f"{us if m['speaker'] == 'agent' else them}: {m['text']}"
                           for m in await db.get_messages(conv_id))
    user = json.dumps({"mode": conv.mode, "current_stage": conv.stage, "stage_goals": STAGE_GOALS[conv.mode],
                       "playbook": conv.playbook, "transcript": transcript}, ensure_ascii=False)
    result = await llm.json_call("director", (PROMPTS / "director.md").read_text(encoding="utf-8"),
                                 user, director_schema(conv.mode), max_tokens=1000)
    if not result:
        return
    stage = result["stage"] if legal_move(conv.mode, conv.stage, result["stage"]) else conv.stage
    if "wind_down" in result["risk_flags"] and conv.mode == "decoy":
        stage = "WIND_DOWN"
    if await db.set_director(conv_id, turn, stage, result["next_objective"][:400], result["risk_flags"]):
        await publish(conv_id, {"type": "stage", "stage": stage, "note": result["next_objective"][:400]})
