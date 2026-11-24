"""Voice calls.

In the browser, with an ElevenLabs API key the page gets a short-lived signed link to a private
agent; without one, the ID of a public agent. For an outbound phone call (a real number ringing),
the server asks ElevenLabs to dial out through its imported Twilio number. In every case the model
endpoint answers only for a voice session that this module opened.
"""
import os
import re

import httpx

from . import db

AGENT_ENV = {"english": "ELEVENLABS_AGENT_EN", "indian_english": "ELEVENLABS_AGENT_EN_IN",
             "emirati": "ELEVENLABS_AGENT_AR"}
E164 = re.compile(r"^\+[1-9]\d{6,14}$")


class VoiceUnavailable(Exception):
    pass


def configured(name):
    """An environment variable's value, treating empty and the placeholder 'unset' as missing."""
    value = os.environ.get(name, "").strip()
    return "" if value.lower() == "unset" else value


def outbound_ready():
    """Real phone calls need the API key and an imported Twilio number's ElevenLabs ID."""
    return bool(configured("ELEVENLABS_API_KEY")) and bool(configured("ELEVENLABS_PHONE_NUMBER_ID"))


async def place_outbound_call(conv_id, to_number):
    """Asks ElevenLabs to call `to_number` through its Twilio number, as the drill's agent.

    ElevenLabs dials out, the agent speaks the opening line, and each turn comes back to this
    server's model endpoint keyed by the conversation ID, exactly like a browser voice call.
    """
    if not E164.match(to_number or ""):
        raise VoiceUnavailable("The number must be in international format, like +9715XXXXXXXX.")
    conv = await db.get_conversation(conv_id)
    if conv is None or conv.status != "active":
        raise VoiceUnavailable("This session is not active.")
    agent_id = configured(AGENT_ENV.get(conv.voice_agent, ""))
    if not agent_id:
        raise VoiceUnavailable("Voice is not configured for this language on the server.")
    api_key, phone_id = configured("ELEVENLABS_API_KEY"), configured("ELEVENLABS_PHONE_NUMBER_ID")
    if not api_key or not phone_id:
        raise VoiceUnavailable("Outbound calls are not set up. Add the ElevenLabs API key and phone number ID.")

    payload = {"agent_id": agent_id, "agent_phone_number_id": phone_id, "to_number": to_number,
               "conversation_initiation_client_data": {
                   "dynamic_variables": {"kameen_conversation_id": conv.id, "opening_line": conv.opening_line}}}
    try:
        async with httpx.AsyncClient(timeout=20) as http:
            reply = await http.post("https://api.elevenlabs.io/v1/convai/twilio/outbound-call",
                                    json=payload, headers={"xi-api-key": api_key})
    except Exception as error:
        raise VoiceUnavailable(f"Could not reach ElevenLabs: {type(error).__name__}")
    if reply.status_code >= 300:
        raise VoiceUnavailable(f"ElevenLabs refused the call ({reply.status_code}).")
    await db.mark_voice(conv_id)                               # opens the voice window and its time limit
    data = reply.json() if reply.content else {}
    return {"call_sid": data.get("callSid"), "elevenlabs_conversation_id": data.get("conversation_id")}


async def start_call(conv_id):
    conv = await db.get_conversation(conv_id)
    if conv is None or conv.status != "active":
        raise VoiceUnavailable("This session is not active.")
    agent_id = configured(AGENT_ENV.get(conv.voice_agent, ""))
    if not agent_id:
        raise VoiceUnavailable("Voice is not configured on this server yet. Text chat still works.")
    reply = {"dynamic_variables": {"kameen_conversation_id": conv.id, "opening_line": conv.opening_line}}

    api_key = configured("ELEVENLABS_API_KEY")
    if api_key:
        async with httpx.AsyncClient(timeout=10) as http:
            signed = await http.get(
                "https://api.elevenlabs.io/v1/convai/conversation/get-signed-url",
                params={"agent_id": agent_id},
                headers={"xi-api-key": api_key},
            )
        if signed.status_code != 200:
            raise VoiceUnavailable(f"ElevenLabs refused the call ({signed.status_code}).")
        reply["signed_url"] = signed.json()["signed_url"]      # valid for 15 minutes
    else:
        reply["agent_id"] = agent_id                           # public agent

    await db.mark_voice(conv_id)                               # opens the voice window and its time limit
    return reply
