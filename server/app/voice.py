"""Voice calls: the server hands the browser a short-lived signed link to a private agent."""
import os

import httpx

from . import db

AGENT_ENV = {"english": "ELEVENLABS_AGENT_EN", "indian_english": "ELEVENLABS_AGENT_EN_IN",
             "emirati": "ELEVENLABS_AGENT_AR"}


class VoiceUnavailable(Exception):
    pass


async def start_call(conv_id):
    conv = await db.get_conversation(conv_id)
    if conv is None or conv.status != "active":
        raise VoiceUnavailable("This session is not active.")
    agent_id = os.environ.get(AGENT_ENV.get(conv.voice_agent, ""), "")
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not agent_id or not api_key:
        raise VoiceUnavailable("Voice is not configured on this server yet. Text chat still works.")
    async with httpx.AsyncClient(timeout=10) as http:
        reply = await http.get(
            "https://api.elevenlabs.io/v1/convai/conversation/get-signed-url",
            params={"agent_id": agent_id},
            headers={"xi-api-key": api_key},
        )
    if reply.status_code != 200:
        raise VoiceUnavailable(f"ElevenLabs refused the call ({reply.status_code}).")
    await db.mark_voice(conv_id)                      # starts the voice time limit
    return {
        "signed_url": reply.json()["signed_url"],     # valid for 15 minutes
        "dynamic_variables": {"kameen_conversation_id": conv.id, "opening_line": conv.opening_line},
    }
