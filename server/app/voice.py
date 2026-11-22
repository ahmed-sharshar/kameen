"""Voice calls.

With an ElevenLabs API key on the server, the browser gets a short-lived signed link to a
private agent. Without one, it gets the ID of a public agent. In both cases the model
endpoint answers only for a voice session that this module opened.
"""
import os

import httpx

from . import db

AGENT_ENV = {"english": "ELEVENLABS_AGENT_EN", "indian_english": "ELEVENLABS_AGENT_EN_IN",
             "emirati": "ELEVENLABS_AGENT_AR"}


class VoiceUnavailable(Exception):
    pass


def configured(name):
    """An environment variable's value, treating empty and the placeholder 'unset' as missing."""
    value = os.environ.get(name, "").strip()
    return "" if value.lower() == "unset" else value


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
