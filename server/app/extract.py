"""Intel extraction: patterns first, then a Haiku pass. Only the scammer's words are read."""
import json
import re

from . import canaries, db, guards, llm
from .events import publish
from .prompting import PROMPTS

IBAN = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]{2})[ -]?(\d{2})((?:[ -]?\d){11,30})(?!\d)")
URL = re.compile(
    r"https?://[^\s<>\"']+"
    r"|(?<![\w@.])(?:[a-z0-9-]+\.)+(?:com|net|org|ae|info|xyz|top|site|online|link|co|io|app|me|shop|live|click)"
    r"(?:/[^\s<>\"']*)?(?![\w-])", re.I)
WALLET = re.compile(
    r"\b(?:bc1[a-z0-9]{25,62}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}|0x[a-fA-F0-9]{40}|T[1-9A-HJ-NP-Za-km-z]{33})\b")
UAE_MOBILE = re.compile(r"^(?:971|00971|0)?5\d{8}$")

TYPES = ["iban", "phone", "url", "payment_link", "wallet", "account", "name", "org"]
SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {
        "type": "object",
        "properties": {"type": {"type": "string", "enum": TYPES},
                       "value": {"type": "string"}, "quote": {"type": "string"}},
        "required": ["type", "value", "quote"], "additionalProperties": False}}},
    "required": ["items"], "additionalProperties": False,
}


def normalise(kind, value):
    value = value.strip()
    if kind in ("iban", "account"):
        return re.sub(r"[^A-Za-z0-9]", "", value).upper()
    if kind == "phone":
        digits = re.sub(r"\D", "", value.translate(guards.EASTERN))
        digits = digits[2:] if digits.startswith("00") else digits
        return "971" + digits[1:] if digits.startswith("05") and len(digits) == 10 else digits
    if kind in ("url", "payment_link"):
        host = re.sub(r"^https?://", "", value.lower()).split("/")[0].split("?")[0]
        return host[4:] if host.startswith("www.") else host
    return value.lower() if kind in ("name", "org") else value


def plausible(kind, value):
    """Does the value have the shape its type claims? A model can mislabel a phrase as an account."""
    count = sum(c.isdigit() for c in value.translate(guards.EASTERN))
    if kind == "iban":
        compact = re.sub(r"[^A-Za-z0-9]", "", value)
        return compact[:2].isalpha() and 15 <= len(compact) <= 34 and count >= 10
    if kind == "account":
        return count >= 8
    if kind == "phone":
        return 7 <= count <= 15
    if kind in ("url", "payment_link"):
        return "." in value and " " not in value.strip()
    if kind == "wallet":
        return len(value.strip()) >= 26 and " " not in value.strip()
    return bool(value.strip())                       # name, org


def _around(text, start, end, margin=40):
    return text[max(0, start - margin):min(len(text), end + margin)].strip()


def find_patterns(text):
    """Returns a list of {type, value, quote, confidence} found by pattern alone."""
    found, taken = [], []

    def free(start, end):
        return all(end <= a or start >= b for a, b in taken)

    for match in IBAN.finditer(text):
        value = re.sub(r"[ -]", "", match.group()).upper()
        if not canaries.iban_ok(value):
            # "...456 5 minutes": the pattern may have run on into the next number. Try shorter.
            shorter = next((value[:n] for n in range(len(value) - 1, 14, -1) if canaries.iban_ok(value[:n])), None)
            value = shorter or value
        if not 15 <= len(value) <= 34:
            continue
        found.append({"type": "iban", "value": value, "quote": _around(text, *match.span()),
                      "confidence": 1.0 if canaries.iban_ok(value) else 0.6})
        taken.append(match.span())
    for match in WALLET.finditer(text):
        if free(*match.span()):
            found.append({"type": "wallet", "value": match.group(), "quote": _around(text, *match.span()),
                          "confidence": 0.9})
            taken.append(match.span())
    for match in URL.finditer(text):
        if free(*match.span()):
            found.append({"type": "url", "value": match.group().rstrip(".,)"),
                          "quote": _around(text, *match.span()), "confidence": 0.9})
            taken.append(match.span())
    # Numbers, including ones spoken as words on a call.
    eastern_free = text.translate(guards.EASTERN)
    for digits, span in guards.digit_runs(text, 9):
        if not free(*span) or len(digits) > 19:
            continue
        plus = eastern_free[max(0, span[0] - 1):span[0]] == "+"
        if UAE_MOBILE.match(digits) or plus or digits.startswith("00"):
            kind = "phone"
        else:
            kind = "phone" if len(digits) <= 12 and digits.startswith("0") else "account"
        found.append({"type": kind, "value": digits, "quote": _around(text, *span), "confidence": 0.8})
    return found


async def _save(conv, item, source, new_items):
    if canaries.is_canary(conv.canary_kit, item["value"]):
        return                                           # never report our own bait
    if not plausible(item["type"], item["value"]):
        return                                           # the label does not fit the value
    normalised = normalise(item["type"], item["value"])
    if not normalised:
        return
    row = {"type": item["type"], "value": item["value"][:300], "normalised_value": normalised[:128],
           "quote": item["quote"][:500], "confidence": item.get("confidence", 0.8), "source": source}
    if await db.add_intel(conv.id, row):
        new_items.append(row)


async def run_extractor(conv_id):
    conv = await db.get_conversation(conv_id)
    if conv is None or conv.mode != "decoy":
        return
    said = [m["text"] for m in await db.get_messages(conv_id) if m["speaker"] == "counterpart"]
    if not said:
        return
    new_items = []
    for item in find_patterns(said[-1]):
        await _save(conv, item, "regex", new_items)

    if llm.enabled():
        recent = "\n".join(said[-2:])
        result = await llm.json_call("live", (PROMPTS / "extractor.md").read_text(encoding="utf-8"),
                                     recent, SCHEMA, max_tokens=1000)
        for item in (result or {}).get("items", []):
            if item["quote"] and item["quote"] in recent:     # the quote check: exact substring only
                await _save(conv, {**item, "confidence": 0.8}, "extractor", new_items)

    for row in new_items:
        await publish(conv_id, {"type": "intel", "intel": {k: row[k] for k in ("type", "value", "quote", "source")}})
