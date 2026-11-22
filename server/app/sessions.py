"""Starting a session: the consent gate for drills, the canary kit for decoys."""
import os
import time

from . import canaries, cards, db, guards

VOICE_BY_LANGUAGE = {"en": "english", "ar": "emirati"}
LANGUAGE_BY_VOICE = {"english": "en", "indian_english": "en", "emirati": "ar"}
LANGUAGE_NAMES = {"en": "English", "ar": "Arabic"}
TEXT_CHANNELS = ("sms", "whatsapp", "email")
CHAT_CHANNELS = ("whatsapp", "sms", "email")          # a chat app reads best with the chat wording


class SessionRefused(Exception):
    pass


async def enrol(person, group_name, handle="", enrolled_by="self", channels=None):
    if not person.strip():
        raise SessionRefused("A name or nickname is needed to enrol.")
    return await db.add_enrolment(person.strip(), group_name.strip(), handle.strip(), enrolled_by,
                                  channels or ["web", "voice"])


async def check_consent(enrolment_id, channel):
    """Every drill passes through here. There is no override."""
    enrolment = await db.get_enrolment(enrolment_id) if enrolment_id else None
    if enrolment is None:
        raise SessionRefused("Drill refused: this person is not enrolled. Drills need recorded consent.")
    now = time.time()
    if enrolment.expires_at < now:
        raise SessionRefused("Drill refused: this person's consent has expired.")
    if channel not in enrolment.channels:
        raise SessionRefused(f"Drill refused: this person did not agree to the {channel} channel.")
    cooldown = float(os.environ.get("DRILL_COOLDOWN_HOURS", "168")) * 3600
    if enrolment.last_drill_at and now - enrolment.last_drill_at < cooldown:
        raise SessionRefused("Drill refused: this person was drilled recently. The cooldown has not passed.")
    return enrolment


def _opening_line(lines, channel):
    if channel == "voice":
        return lines.get("voice", "")
    for key in (CHAT_CHANNELS if channel == "telegram" else TEXT_CHANNELS):
        if lines.get(key):
            return lines[key]
    return lines.get("text", "")


async def start_conversation(mode, persona_id=None, scenario_id=None, enrolment_id=None,
                             channel="web", external_id=None, voice=None):
    if mode == "decoy":
        persona = cards.persona(persona_id or "rajesh")
        if persona is None:
            raise SessionRefused("Unknown persona.")
        # In text the scammer writes first. On a call the persona answers the phone.
        opening = persona["opening_line"]["voice"] if channel == "voice" else ""
        conv = await db.create_conversation(
            mode="decoy", channel=channel, language=persona["language"], persona_id=persona["id"],
            scenario_id=scenario_id if cards.scenario(scenario_id or "") else None,
            external_id=external_id, stage="HOOKED", voice_agent=persona["voice_agent"],
            opening_line=opening, canary_kit=canaries.new_kit())
        marker = "[call connected]"

    elif mode == "drill":
        original = cards.scenario(scenario_id or "")
        if original is None:
            raise SessionRefused("Unknown scenario.")
        # The chosen voice sets the language of the whole drill: an Arabic voice means an Arabic drill.
        voice = voice if voice in LANGUAGE_BY_VOICE else None
        language = LANGUAGE_BY_VOICE.get(voice, original["language"])
        card = cards.scenario(original["id"], language)
        if card["language"] != language:
            raise SessionRefused(f"Drill refused: this scenario has no {LANGUAGE_NAMES[language]} version yet.")
        if not card.get("approved_by"):
            raise SessionRefused(f"Drill refused: the {LANGUAGE_NAMES[language]} version of this scenario card "
                                 "has not been approved.")
        await check_consent(enrolment_id, channel if channel in ("voice", "telegram") else "web")
        opening = _opening_line(card["opening_line"], channel)
        conv = await db.create_conversation(
            mode="drill", channel=channel, language=card["language"], scenario_id=card["id"],
            enrolment_id=enrolment_id, external_id=external_id, stage="PRETEXT",
            voice_agent=voice or card.get("voice_agent") or VOICE_BY_LANGUAGE.get(card["language"], "english"),
            opening_line=opening, agent_digits=[d for d, _ in guards.digit_runs(opening, 4)])
        marker = "[call connected]" if channel == "voice" else "[conversation started]"

    else:
        raise SessionRefused("Mode must be decoy or drill.")

    if conv.opening_line:
        # The model's history must start with the other side, so a marker comes first.
        await db.add_message(conv.id, "marker", marker)
        await db.add_message(conv.id, "agent", conv.opening_line)
    return conv
