"""Telegram text channel. Decoy mode only: the person messaging the bot plays the scammer."""
import os

import httpx

from . import agent, db, sessions

INTRO = ("Kameen decoy test. You play the scammer; an AI persona will answer. "
         "This is a simulation. Send your first message to begin, or /start to restart.")


async def send(chat_id, text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token or not text:
        return
    async with httpx.AsyncClient(timeout=10) as http:
        await http.post(f"https://api.telegram.org/bot{token}/sendMessage",
                        json={"chat_id": chat_id, "text": text})


async def handle(update):
    message = update.get("message") or {}
    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")
    if not text or chat_id is None:
        return
    external_id = f"tg:{chat_id}"
    conv = await db.find_by_external(external_id)
    if text.startswith("/start") or conv is None:
        if conv is not None:
            await db.end_conversation(conv.id)
        await sessions.start_conversation(mode="decoy", persona_id="rajesh", channel="telegram",
                                          external_id=external_id)
        await send(chat_id, INTRO)
        return
    parts = [s async for s in agent.agent_turn_stream(conv.id, text)]
    await send(chat_id, " ".join(parts))
