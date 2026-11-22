"""Scenario and persona cards, loaded once from JSON files."""
import json
from pathlib import Path

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
