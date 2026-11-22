"""Telegram: a real messaging channel, used two ways.

Decoy: anyone who writes to the bot is treated as a scammer and gets a persona that stalls them.

Surprise drill: a person opens an organiser's invite link, reads what will happen and replies AGREE.
At an unannounced moment inside the organiser's window the bot sends one simulated scam message.
The drill then runs like any other: it stops before anything real is shared, reveals itself and
teaches the lesson. A person who agreed is never sent to the decoy, and /leave withdraws at once.
"""
import hashlib
import os
import random
import re
import secrets
import time

import httpx

from . import agent, cards, db, llm, sessions
from .director import make_playbook

BOT = {"username": None}
QUIET_HOURS = 12                    # a drill message nobody answered is closed, and revealed, after this long
AGREE = re.compile(r"^\W*((yes,? )?i agree|agree|أوافق|اوافق|موافق)\W*$", re.I)

DECOY_INTRO = ("Kameen decoy test. You play the scammer; an AI persona will answer. "
               "This is a simulation. Send your first message to begin, or /start to restart.")
# Arabic lines are drafts: a native Emirati speaker must review them.
TEXT = {
    "en": {
        "consent": "Kameen safety drill for {group}. If you agree, you will get ONE simulated scam message in this "
                   "chat at some point in the next {window}. It will not be marked as a drill. It stops before you "
                   "share anything real, then tells you it was a drill and what to watch for. Only group totals are "
                   "reported, never your name. Reply AGREE to take part. Any other reply keeps you out.",
        "joined": "You are enrolled. The drill message will arrive within {window}. Send /leave at any time to withdraw.",
        "declined": "You have not been enrolled. Open the invite link again if you change your mind.",
        "waiting": "You are enrolled in a Kameen drill. There is nothing to do now. Send /leave to withdraw.",
        "left": "You have left. No more drill messages will be sent to you.",
        "not_enrolled": "You are not enrolled in a drill.",
        "invalid": "This invite link is not valid or has expired.",
        "already": "You are already enrolled. Send /leave first if you want to start again.",
        "units": {"minutes": "{n} minutes", "hours": "{n} hours", "days": "{n} days"},
    },
    "ar": {
        "consent": "تمرين توعوي من كمين لمجموعة {group}. إذا وافقت، بتوصلك رسالة احتيال وهمية وحدة في هالمحادثة في أي "
                   "وقت خلال {window}. الرسالة ما بتكون معلّمة إنها تمرين. التمرين يوقف قبل لا تشارك أي شي حقيقي، "
                   "وعقبها يخبرك إنه تمرين وشو تنتبه له. النتايج تنعرض كمجموع للمجموعة بس، بدون اسمك. "
                   "رد بكلمة «أوافق» عشان تشارك. أي رد ثاني يعني إنك ما تبي تشارك.",
        "joined": "تم تسجيلك. رسالة التمرين بتوصلك خلال {window}. طرّش /leave في أي وقت عشان تنسحب.",
        "declined": "ما تم تسجيلك. افتح رابط الدعوة مرة ثانية إذا غيرت رايك.",
        "waiting": "إنت مسجل في تمرين كمين. ما في شي مطلوب منك الحين. طرّش /leave عشان تنسحب.",
        "left": "تم انسحابك. ما بتوصلك أي رسايل تمرين ثانية.",
        "not_enrolled": "إنت مب مسجل في أي تمرين.",
        "invalid": "رابط الدعوة مب صحيح أو انتهت مدته.",
        "already": "إنت مسجل من قبل. طرّش /leave أول إذا تبي تبدا من يديد.",
        "units": {"minutes": "{n} دقيقة", "hours": "{n} ساعة", "days": "{n} يوم"},
    },
}


def configured():
    return os.environ.get("TELEGRAM_BOT_TOKEN", "unset") not in ("", "unset")


def webhook_secret():
    """What Telegram must send with every update. Telegram accepts only letters, digits, "_" and "-",
    and a generated secret may hold other characters, so its hash is used instead."""
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    return hashlib.sha256(secret.encode()).hexdigest() if secret else ""


async def call(method, payload):
    """One Telegram Bot API call. Returns the result, or None. The token never reaches a log line."""
    if not configured():
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            reply = await http.post(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{method}",
                                    json=payload)
        data = reply.json()
    except Exception as error:
        llm.log(f"telegram {method} failed:", type(error).__name__)
        return None
    if not data.get("ok"):
        llm.log(f"telegram {method} refused:", data.get("description", ""))
        return None
    return data.get("result")


async def send(chat_id, text):
    if text:
        await call("sendMessage", {"chat_id": chat_id, "text": text})


async def setup():
    """At start-up: learn the bot's name and point Telegram at this server. Needs no manual step."""
    me = await call("getMe", {})
    if not me:
        return
    BOT["username"] = me.get("username")
    base = (os.environ.get("PUBLIC_URL") or os.environ.get("RENDER_EXTERNAL_URL") or "").rstrip("/")
    secret = webhook_secret()
    if base and secret:
        done = await call("setWebhook", {"url": base + "/telegram/webhook", "secret_token": secret,
                                         "allowed_updates": ["message"]})
        llm.log("telegram bot @%s, webhook %s" % (BOT["username"], "set" if done else "not set"))


def link(code):
    return f"https://t.me/{BOT['username']}?start={code}" if BOT["username"] else None


def window_text(minutes, language):
    units = TEXT[language]["units"]
    if minutes < 120:
        return units["minutes"].format(n=minutes)
    if minutes < 2880:
        return units["hours"].format(n=round(minutes / 60))
    return units["days"].format(n=round(minutes / 1440))


async def new_invite(group_name, scenario_id, language, window_minutes):
    code = secrets.token_urlsafe(8).replace("-", "a").replace("_", "b")
    await db.add_invite(code, group_name, scenario_id, language, window_minutes)
    return code


# ---- incoming messages -------------------------------------------------------

async def handle(update):
    message = update.get("message") or {}
    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")
    if not text or chat_id is None:
        return
    chat = f"tg:{chat_id}"
    command, _, argument = text.partition(" ")

    if command == "/start" and argument.strip():
        return await offer(chat_id, chat, argument.strip())
    if command == "/leave":
        return await leave(chat_id, chat)

    pending = await db.get_value("join:" + chat)
    if pending:                                              # they were shown the consent text and now answer it
        await db.drop_value("join:" + chat)
        if AGREE.match(text):
            return await join(chat_id, chat, pending["code"])
        return await send(chat_id, TEXT[pending.get("language", "en")]["declined"])

    conv = await db.find_by_external(chat)
    if conv is not None and conv.mode == "drill":           # the drill is on: this is the trainee's reply
        parts = [s async for s in agent.agent_turn_stream(conv.id, text)]
        return await send(chat_id, " ".join(parts))
    if await db.find_enrolment(chat, "telegram"):           # agreed to a drill: never the decoy
        return await send(chat_id, TEXT[await db.chat_language(chat)]["waiting"])

    if command == "/start" or conv is None:                 # anyone else plays the scammer against the decoy
        if conv is not None:
            await db.end_conversation(conv.id)
        await sessions.start_conversation(mode="decoy", persona_id="rajesh", channel="telegram", external_id=chat)
        return await send(chat_id, DECOY_INTRO)
    parts = [s async for s in agent.agent_turn_stream(conv.id, text)]
    await send(chat_id, " ".join(parts))


async def offer(chat_id, chat, code):
    """Someone opened an invite link. Show exactly what they would be agreeing to."""
    invite = await db.get_invite(code)
    if invite is None:
        return await send(chat_id, TEXT["en"]["invalid"])
    words = TEXT[invite.language]
    if await db.find_enrolment(chat, "telegram"):
        return await send(chat_id, words["already"])
    await db.put_value("join:" + chat, {"code": code, "language": invite.language})
    await send(chat_id, words["consent"].format(
        group=invite.group_name, window=window_text(invite.window_minutes, invite.language)))


async def join(chat_id, chat, code):
    """They replied AGREE. Record the consent and pick the moment."""
    invite = await db.get_invite(code)
    if invite is None:
        return await send(chat_id, TEXT["en"]["invalid"])
    approved = [c["id"] for c in cards.SCENARIOS.values() if cards.scenario(c["id"], invite.language).get("approved_by")
                and cards.scenario(c["id"], invite.language)["language"] == invite.language]
    scenario_id = invite.scenario_id if invite.scenario_id in approved else (random.choice(approved) if approved else None)
    if scenario_id is None:
        return await send(chat_id, TEXT["en"]["invalid"])
    # No name is kept: the chat is the only link to the person, and results are reported by group.
    enrolment_id = await sessions.enrol("Telegram member", invite.group_name, handle=chat, channels=["telegram"])
    seconds = invite.window_minutes * 60
    await db.add_scheduled(code, enrolment_id, chat, scenario_id, invite.language,
                           time.time() + random.uniform(0.15 * seconds, seconds))
    conv = await db.find_by_external(chat)
    if conv is not None:                                     # a decoy chat they had open is closed
        await db.end_conversation(conv.id)
    await send(chat_id, TEXT[invite.language]["joined"].format(
        window=window_text(invite.window_minutes, invite.language)))


async def leave(chat_id, chat):
    language = await db.chat_language(chat)
    await db.drop_value("join:" + chat)
    conv = await db.find_by_external(chat)
    if conv is not None and conv.mode == "drill":           # a drill never just stops: reveal it first
        await send(chat_id, " ".join([line async for line in agent.reveal_and_teach(conv, "stopped")]))
    ended = await db.withdraw(chat)
    await send(chat_id, TEXT[language]["left" if ended else "not_enrolled"])


# ---- the clock ---------------------------------------------------------------

async def send_due():
    """Sends every drill whose moment has come. Consent is checked again at that moment."""
    sent = 0
    for drill in await db.due_drills():
        try:
            conv = await sessions.start_conversation(
                mode="drill", scenario_id=drill.scenario_id, enrolment_id=drill.enrolment_id, channel="telegram",
                external_id=drill.chat, voice="emirati" if drill.language == "ar" else "english")
        except sessions.SessionRefused as reason:           # withdrawn, expired or still in the cooldown
            llm.log("scheduled drill not sent:", str(reason))
            await db.mark_scheduled(drill.id, "refused")
            continue
        await db.mark_scheduled(drill.id, "sent", conv.id)
        agent.run_later(make_playbook(conv.id))
        await send(drill.chat[3:], conv.opening_line)
        sent += 1
    return sent


async def close_unanswered(quiet_seconds=QUIET_HOURS * 3600):
    """A drill message nobody answered: tell the person it was a drill, and that ignoring it was right."""
    closed = 0
    for conv_id, mode, channel, quiet in await db.idle_conversations():
        if mode != "drill" or channel != "telegram" or quiet < quiet_seconds:
            continue
        conv = await db.get_conversation(conv_id)
        outcome = "ignored" if conv.turn_count == 0 else "stopped"
        text = " ".join([line async for line in agent.reveal_and_teach(conv, outcome)])
        await send((conv.external_id or "")[3:], text)
        closed += 1
    return closed
