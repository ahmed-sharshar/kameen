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


def scenario(scenario_id):
    return SCENARIOS.get(scenario_id)


def public_list():
    """What the website may see: no playbooks, no commit signals."""
    return {
        "personas": [
            {k: p.get(k) for k in ("id", "name", "age", "language", "voice_agent", "background")}
            for p in PERSONAS.values()
        ],
        "scenarios": [
            {**{k: s.get(k) for k in ("id", "title", "impersonates", "channels", "language", "difficulty")},
             "approved": bool(s.get("approved_by"))}
            for s in SCENARIOS.values()
        ],
    }
