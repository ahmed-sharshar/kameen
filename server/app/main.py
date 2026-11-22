"""Routes. Run from the server/ folder: uvicorn app.main:app --reload"""
import hmac
import json
import os
import re
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

from . import agent, campaigns, cards, db, evidence, llm, sessions, telegram, voice
from .director import make_playbook
from .events import publish, subscribe

ACCESS_CODE = os.environ["ACCESS_CODE"]                 # the server refuses to start without one
ORIGINS = [o.strip() for o in os.environ.get("FRONTEND_ORIGIN", "http://localhost:5500").split(",") if o.strip()]
SESSIONS_PER_HOUR = 30
VOICE_WINDOW_SECONDS = 20 * 60
recent_starts = {}


@asynccontextmanager
async def lifespan(_app):
    await db.init()
    yield


app = FastAPI(title="Kameen", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["*"], allow_headers=["*"])


def require_code(x_access_code: str = Header(None)):
    if not hmac.compare_digest(x_access_code or "", ACCESS_CODE):
        raise HTTPException(401, "Wrong access code")


def require_admin(x_admin_code: str = Header(None)):
    expected = os.environ.get("ADMIN_CODE", "")
    if not expected or not hmac.compare_digest(x_admin_code or "", expected):
        raise HTTPException(401, "Wrong admin code")


def rate_limit(request: Request):
    """A few sessions per visitor per hour. In memory, which is enough for one server."""
    who = request.client.host if request.client else "unknown"
    now = time.time()
    starts = [t for t in recent_starts.get(who, []) if now - t < 3600]
    if len(starts) >= SESSIONS_PER_HOUR:
        raise HTTPException(429, "Too many sessions from this address. Try again later.")
    recent_starts[who] = starts + [now]


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/cards", dependencies=[Depends(require_code)])
async def list_cards():
    return cards.public_list()


@app.post("/enrolments", dependencies=[Depends(require_code)])
async def new_enrolment(body: dict):
    try:
        enrolment_id = await sessions.enrol(
            person=str(body.get("person", "")), group_name=str(body.get("group_name", "")),
            handle=str(body.get("handle", "")), enrolled_by="self")
    except sessions.SessionRefused as reason:
        raise HTTPException(400, str(reason))
    return {"enrolment_id": enrolment_id}


@app.post("/sessions", dependencies=[Depends(require_code), Depends(rate_limit)])
async def new_session(body: dict):
    try:
        conv = await sessions.start_conversation(
            mode=body.get("mode"),                        # "decoy" or "drill"
            persona_id=body.get("persona_id"),
            scenario_id=body.get("scenario_id"),
            enrolment_id=body.get("enrolment_id"),        # required for drills
            channel="voice" if body.get("channel") == "voice" else "web",
        )
    except sessions.SessionRefused as reason:             # no consent, cooldown, unapproved card
        raise HTTPException(403, str(reason))
    agent.run_later(make_playbook(conv.id))
    return {"conversation_id": conv.id, "opening_line": conv.opening_line}


@app.post("/chat", dependencies=[Depends(require_code)])
async def chat(body: dict):
    conv_id = str(body.get("conversation_id", ""))
    parts = [s async for s in agent.agent_turn_stream(conv_id, str(body.get("text", "")))]
    await agent.wait_saved(conv_id)
    conv = await db.get_conversation(conv_id)
    if conv is None:
        raise HTTPException(404, "Unknown conversation")
    return {"reply": " ".join(parts), "status": "active" if conv.status == "active" else "ended"}


@app.post("/voice/session", dependencies=[Depends(require_code)])
async def voice_session(body: dict):
    try:
        return await voice.start_call(str(body.get("conversation_id", "")))   # signed_url, dynamic_variables
    except voice.VoiceUnavailable as reason:
        raise HTTPException(503, str(reason))


@app.post("/sessions/{conv_id}/kill", dependencies=[Depends(require_code)])
async def kill(conv_id: str):
    await db.end_conversation(conv_id, status="killed")
    await publish(conv_id, {"type": "ended", "reason": "killed by operator"})
    return {"ok": True}


@app.post("/sessions/{conv_id}/rating", dependencies=[Depends(require_code)])
async def rating(conv_id: str, body: dict):
    await db.set_rating(conv_id, str(body.get("text", "")))
    return {"ok": True}


@app.get("/sessions", dependencies=[Depends(require_code)])
async def list_sessions():
    return {"sessions": await db.list_conversations()}


@app.get("/sessions/{conv_id}", dependencies=[Depends(require_code)])
async def session_detail(conv_id: str):
    conv = await db.get_conversation(conv_id)
    if conv is None:
        raise HTTPException(404, "Unknown conversation")
    return {
        "conversation": {k: getattr(conv, k) for k in (
            "id", "mode", "channel", "persona_id", "scenario_id", "stage", "status", "turn_count",
            "started_at", "director_note", "opening_line")},
        "messages": await db.get_messages(conv_id),
        "intel": await db.list_intel(conv_id),
        "canaries": await db.list_canaries(conv_id),
        "drill_result": await db.get_drill_result(conv_id),
    }


# A new browser tab cannot send headers, so this page is keyed by the unguessable conversation ID.
@app.get("/sessions/{conv_id}/evidence", response_class=HTMLResponse)
async def evidence_pack(conv_id: str):
    conv = await db.get_conversation(conv_id)
    if conv is None:
        raise HTTPException(404, "Unknown conversation")
    return evidence.render(conv, await db.get_messages(conv_id), await db.list_intel(conv_id),
                           await db.list_canaries(conv_id))


@app.get("/campaigns", dependencies=[Depends(require_code)])
async def campaign_graph():
    return await campaigns.graph()


@app.get("/drills/summary", dependencies=[Depends(require_code)])
async def drills_summary():
    results = await db.list_drill_results()
    minimum = int(os.environ.get("DRILL_MIN_GROUP", "5"))
    at_risk = {"would_comply", "attempted_disclosure"}
    by_outcome, by_scenario, by_group = {}, {}, {}
    for r in results:
        by_outcome[r["outcome"]] = by_outcome.get(r["outcome"], 0) + 1
        for table, key in ((by_scenario, r["scenario_id"]), (by_group, r["group"] or "No group")):
            row = table.setdefault(key, {"total": 0, "at_risk": 0})
            row["total"] += 1
            row["at_risk"] += r["outcome"] in at_risk
    # Aggregates only: groups smaller than the minimum are folded together.
    small = {"group": "Smaller groups (combined)", "total": 0, "at_risk": 0}
    groups = []
    for name, row in sorted(by_group.items()):
        if row["total"] >= minimum:
            groups.append({"group": name, **row})
        else:
            small["total"] += row["total"]
            small["at_risk"] += row["at_risk"]
    if small["total"]:
        groups.append(small)
    return {
        "total": len(results), "by_outcome": by_outcome, "min_group": minimum, "by_group": groups,
        "by_scenario": [{"scenario_id": sid, "title": (cards.scenario(sid) or {}).get("title", sid), **row}
                        for sid, row in sorted(by_scenario.items(), key=lambda kv: str(kv[0]))],
    }


@app.get("/eval/latest", dependencies=[Depends(require_code)])
async def eval_latest():
    return await db.get_value("eval") or {}


@app.post("/eval", dependencies=[Depends(require_admin)])
async def eval_upload(body: dict):
    await db.put_value("eval", body)
    return {"ok": True}


CONV_ID = re.compile(r"kameen_conversation_id=([0-9a-f-]{36})")


def find_conversation_id(body):
    extra = body.get("elevenlabs_extra_body") or {}
    if extra.get("kameen_conversation_id"):
        return extra["kameen_conversation_id"]
    for message in body.get("messages", []):
        if message.get("role") == "system":
            found = CONV_ID.search(str(message.get("content", "")))
            if found:
                return found.group(1)
    raise HTTPException(400, "No conversation ID in the request")


# ElevenLabs Custom LLM calls this for every voice turn.
@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def completions(request: Request, authorization: str = Header(None)):
    body = await request.json()
    try:
        conv_id = find_conversation_id(body)
    except HTTPException:
        conv_id = None
    conv = await db.get_conversation(conv_id) if conv_id else None

    # Who may call this endpoint (decided by the project owner on 2026-11-22):
    # the request must name a voice session that /voice/session opened in the last 20 minutes.
    # That ID is random, short-lived and only handed out behind the access code.
    # The shared secret is still checked when the agent sends it, and VOICE_REQUIRE_SECRET=1
    # makes it mandatory again.
    secret = os.environ.get("LLM_SHARED_SECRET", "").strip()
    scheme, _, token = (authorization or "").partition(" ")
    has_secret = bool(secret) and scheme.lower() == "bearer" and hmac.compare_digest(token.strip(), secret)
    live_voice = (conv is not None and conv.status == "active" and conv.voice_started_at is not None
                  and time.time() - conv.voice_started_at < VOICE_WINDOW_SECONDS)
    strict = os.environ.get("VOICE_REQUIRE_SECRET") == "1"
    allowed = live_voice and (has_secret or not strict)
    # Shapes only, never values.
    llm.log("voice request on", request.url.path, "| allowed:", allowed, "| live voice session:", live_voice,
            "| secret ok:", has_secret, "| body keys:", sorted(body.keys()),
            "| roles:", [m.get("role") for m in body.get("messages", [])],
            "| extra body:", sorted((body.get("elevenlabs_extra_body") or {}).keys()))
    if not allowed:
        raise HTTPException(401)
    user_text = next((str(m.get("content", "")) for m in reversed(body.get("messages", []))
                      if m.get("role") == "user"), "")

    async def stream():
        base = {"id": f"kameen-{conv_id}", "object": "chat.completion.chunk",
                "created": int(time.time()), "model": "kameen"}
        async for sentence in agent.agent_turn_stream(conv_id, user_text):
            chunk = {**base, "choices": [{"index": 0, "delta": {"content": sentence + " "}, "finish_reason": None}]}
            yield f"data: {json.dumps(chunk)}\n\n"
        done = {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
        yield f"data: {json.dumps(done)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


# The website listens here for live messages, intel, stage changes and guardrail events.
@app.get("/events/stream")
async def events(conversation_id: str):
    async def stream():
        async for event in subscribe(conversation_id):
            yield f"data: {json.dumps(event)}\n\n" if event else ": ping\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(None)):
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    if not secret or not hmac.compare_digest(x_telegram_bot_api_secret_token or "", secret):
        raise HTTPException(401)
    await telegram.handle(await request.json())
    return {"ok": True}
