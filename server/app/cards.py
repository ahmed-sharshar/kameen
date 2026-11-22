"""Scenario and persona cards, loaded once from JSON files."""
import json
import re
from pathlib import Path

from . import guards

ROOT = Path(__file__).parent / "cards"


def _load(folder):
    cards = {}
    for path in sorted((ROOT / folder).glob("*.json")):
        card = json.loads(path.read_text(encoding="utf-8"))
        cards[card["id"]] = card
    return cards


PERSONAS = _load("personas")
SCENARIOS = _load("scenarios")


def persona(persona_id):
    return PERSONAS.get(persona_id)


def scenario(scenario_id, language=None):
    """A scenario card. With a language it has a translation for, the translated fields replace
    the originals, including approved_by: each language is approved on its own."""
    card = SCENARIOS.get(scenario_id)
    if card is None or not language or language == card.get("language"):
        return card
    local = (card.get("translations") or {}).get(language)
    return {**card, **local, "language": language} if local else card


def languages(card):
    """Every language a card exists in, and whether that version is approved."""
    found = {card.get("language", "en"): bool(card.get("approved_by"))}
    for code, local in (card.get("translations") or {}).items():
        found[code] = bool(local.get("approved_by"))
    return found


CHANNELS = {"voice", "sms", "whatsapp", "email"}
ARABIC = re.compile(r"[\u0600-\u06FF]")


def _version_problems(version, name, channels):
    """One language version of a card: what the trainee is shown and what Kameen listens for."""
    found = []
    lines = version.get("opening_line") or {}
    for channel in channels:
        if not str(lines.get(channel) or "").strip():
            found.append(f"{name}: no opening line for the {channel} channel")
    question = str(version.get("commit_question") or "").strip()
    if not question.endswith(("?", "؟")):
        found.append(f"{name}: the commit question must be a question")
    for label, text in [("commit question", question)] + [(f"{c} opening line", str(t)) for c, t in lines.items()]:
        if guards.ASKS_FOR_SECRET.search(text):
            found.append(f"{name}: the {label} asks for a secret")
        if guards.gives_payment_detail(text):
            found.append(f"{name}: the {label} contains a link, an account or a long number")
        if guards.SELF_REVEAL.search(text):
            found.append(f"{name}: the {label} gives the drill away")
    if len(version.get("commit_signals") or []) < 3:
        found.append(f"{name}: at least three commit signals are needed")
    if len(version.get("red_flags") or []) != 3:
        found.append(f"{name}: exactly three red flags are needed")
    lesson = version.get("lesson") or {}
    if not lesson.get("headline") or len(lesson.get("three_points") or []) != 3 or not lesson.get("report_to"):
        found.append(f"{name}: the lesson needs a headline, three points and where to report")
    return found


def problems(card):
    """Why a scenario card may not be used, as plain sentences. An empty list means it is sound."""
    found = []
    if not re.fullmatch(r"scn_[a-z0-9_]+_v\d+", str(card.get("id", ""))):
        found.append("the id must look like scn_some_name_v1")
    for field in ("title", "scam_type", "impersonates", "hook", "ask"):
        if not str(card.get(field) or "").strip():
            found.append(f"{field} is missing")
    channels = card.get("channels") or []
    if not channels or not set(channels) <= CHANNELS:
        found.append("channels must be one or more of " + ", ".join(sorted(CHANNELS)))
    if "voice" not in channels or len(channels) < 2:
        found.append("a card needs the voice channel and at least one text channel: the site offers both")
    if set(card.get("stage_goals") or {}) != {"PRETEXT", "PRESSURE", "ASK"}:
        found.append("stage_goals needs PRETEXT, PRESSURE and ASK")
    found += _version_problems(card, "English", channels)
    for code, local in (card.get("translations") or {}).items():
        name = {"ar": "Arabic"}.get(code, code)
        found += _version_problems(local, name, channels)
        if len(local.get("commit_signals") or []) != len(card.get("commit_signals") or []):
            found.append(f"{name}: commit signals must match the English list, line for line")
        if code == "ar":
            spoken = [local.get("commit_question", ""), local.get("lesson", {}).get("headline", ""),
                      *(local.get("opening_line") or {}).values(), *(local.get("red_flags") or [])]
            if not all(ARABIC.search(str(text)) for text in spoken):
                found.append("Arabic: some lines are not in Arabic")
    return found


def public_list():
    """What the website may see: no playbooks, no commit signals."""
    return {
        "personas": [
            {k: p.get(k) for k in ("id", "name", "age", "language", "voice_agent", "background")}
            for p in PERSONAS.values()
        ],
        "scenarios": [
            {**{k: s.get(k) for k in ("id", "title", "impersonates", "channels", "language", "difficulty")},
             "approved": bool(s.get("approved_by")), "languages": languages(s)}
            for s in SCENARIOS.values()
        ],
    }
