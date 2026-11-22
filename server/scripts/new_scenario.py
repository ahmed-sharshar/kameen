"""Drafts a new scenario card with the playbook model. A person must approve it before any drill uses it.

Usage (from server/):
    .venv/bin/python scripts/new_scenario.py rental_deposit "A fake landlord wants a deposit before any viewing."

Writes app/cards/scenarios/scn_rental_deposit_v1.json with "approved_by": null in both languages.
Costs a few cents of API use. Nothing is written if the draft breaks a card rule.
"""
import asyncio
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv                       # noqa: E402

load_dotenv(ROOT / ".env")

from app import cards, llm                           # noqa: E402

REPORT_TO = {"en": "contact the Aman service of Abu Dhabi Police", "ar": "تواصل مع خدمة أمان في شرطة أبوظبي"}
CHANNELS = sorted(cards.CHANNELS)
TEXT = {"type": "string"}
TEXTS = {"type": "array", "items": TEXT}
OPENINGS = {"type": "array", "items": {
    "type": "object", "properties": {"channel": {"type": "string", "enum": CHANNELS}, "text": TEXT},
    "required": ["channel", "text"], "additionalProperties": False}}
LESSON = {"type": "object", "properties": {"headline": TEXT, "three_points": TEXTS},
          "required": ["headline", "three_points"], "additionalProperties": False}
LOCAL = {"opening_lines": OPENINGS, "commit_question": TEXT, "commit_signals": TEXTS, "red_flags": TEXTS, "lesson": LESSON}
SCHEMA = {
    "type": "object",
    "properties": {
        "title": TEXT, "scam_type": TEXT, "impersonates": TEXT,
        "channels": {"type": "array", "items": {"type": "string", "enum": CHANNELS}},
        "hook": TEXT, "pressure_tactics": TEXTS,
        "stage_goals": {"type": "object", "properties": {"PRETEXT": TEXT, "PRESSURE": TEXT, "ASK": TEXT},
                        "required": ["PRETEXT", "PRESSURE", "ASK"], "additionalProperties": False},
        "ask": TEXT, **LOCAL,
        "decoy_targets": {"type": "array", "items": {
            "type": "string", "enum": ["iban", "callback_number", "payment_link", "wallet", "name"]}},
        "difficulty": {"type": "integer"},
        "arabic": {"type": "object", "properties": LOCAL, "required": list(LOCAL), "additionalProperties": False},
    },
    "required": ["title", "scam_type", "impersonates", "channels", "hook", "pressure_tactics", "stage_goals", "ask",
                 *LOCAL, "decoy_targets", "difficulty", "arabic"],
    "additionalProperties": False,
}


def _local(draft, language):
    return {
        "opening_line": {line["channel"]: line["text"] for line in draft["opening_lines"]},
        "commit_question": draft["commit_question"],
        "commit_signals": [signal.lower() for signal in draft["commit_signals"]],
        "red_flags": draft["red_flags"],
        "lesson": {**draft["lesson"], "report_to": REPORT_TO[language]},
    }


def build(name, draft):
    """The card file, from the model's draft. Nothing in it is approved."""
    english, arabic = _local(draft, "en"), _local(draft["arabic"], "ar")
    return {
        "id": f"scn_{name}_v1", "title": draft["title"], "scam_type": draft["scam_type"],
        "impersonates": draft["impersonates"], "channels": draft["channels"], "language": "en",
        "difficulty": max(1, min(3, draft["difficulty"])), "hook": draft["hook"],
        "opening_line": english["opening_line"], "pressure_tactics": draft["pressure_tactics"],
        "stage_goals": draft["stage_goals"], "ask": draft["ask"],
        "commit_question": english["commit_question"], "commit_signals": english["commit_signals"],
        "red_flags": english["red_flags"], "lesson": english["lesson"],
        "decoy_targets": draft["decoy_targets"], "source_ref": "drafted by scripts/new_scenario.py",
        "approved_by": None,
        "translations": {"ar": {"approved_by": None, **arabic}},
    }


async def main():
    if len(sys.argv) != 3 or not re.fullmatch(r"[a-z0-9_]+", sys.argv[1]):
        sys.exit('Usage: new_scenario.py short_name "description of the scam"')
    name, description = sys.argv[1], sys.argv[2]
    target = ROOT / "app" / "cards" / "scenarios" / f"scn_{name}_v1.json"
    if target.exists():
        sys.exit(f"{target.name} already exists. Pick another name, or delete it first.")
    if not llm.enabled():
        sys.exit("No ANTHROPIC_API_KEY in server/.env: drafting a card needs the model.")
    example = {k: v for k, v in cards.scenario("scn_bank_otp_v1").items() if k not in ("approved_by", "source_ref")}
    draft = await llm.json_call(
        "playbook", (ROOT / "app" / "prompts" / "scenario_generator.md").read_text(encoding="utf-8"),
        json.dumps({"scam": description, "example_card": example}, ensure_ascii=False),
        SCHEMA, max_tokens=8000, effort="medium")
    if not draft:
        sys.exit("The model returned no card. Try again, or reword the description.")
    card = build(name, draft)
    found = cards.problems(card)
    if found:
        print(json.dumps(card, ensure_ascii=False, indent=2))
        sys.exit("Not saved. The draft breaks these rules:\n- " + "\n- ".join(found))
    target.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {target.name}: {card['title']}. It stays unusable until someone sets approved_by.")


if __name__ == "__main__":
    asyncio.run(main())
