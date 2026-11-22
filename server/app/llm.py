"""One place for model names and the Anthropic client."""
import json
import os
import sys

from anthropic import AsyncAnthropic

DEFAULTS = {"live": ("LIVE_MODEL", "claude-haiku-5-5"),
            "director": ("DIRECTOR_MODEL", "claude-sonnet-5-5"),
            "playbook": ("PLAYBOOK_MODEL", "claude-opus-5-5")}
_client = None

# Test hooks. USAGE adds up tokens per model. TRACE, when set to a list, collects the text of
# every request the app sends to a model, so a test can prove a secret never reached one.
USAGE = {}
TRACE = None


def record(model_name, usage):
    if usage is None:
        return
    row = USAGE.setdefault(model_name, {"calls": 0, "input": 0, "output": 0, "cache_read": 0, "cache_write": 0})
    row["calls"] += 1
    row["input"] += getattr(usage, "input_tokens", 0) or 0
    row["output"] += getattr(usage, "output_tokens", 0) or 0
    row["cache_read"] += getattr(usage, "cache_read_input_tokens", 0) or 0
    row["cache_write"] += getattr(usage, "cache_creation_input_tokens", 0) or 0


def trace(*parts):
    if TRACE is not None:
        TRACE.append("\n".join(str(part) for part in parts))


def enabled():
    """False means: no API key, or the scripted fake model was asked for."""
    return bool(os.environ.get("ANTHROPIC_API_KEY")) and os.environ.get("KAMEEN_FAKE_MODEL") != "1"


def client():
    global _client
    if _client is None:
        _client = AsyncAnthropic()                 # reads ANTHROPIC_API_KEY
    return _client


def model(role):
    variable, default = DEFAULTS[role]
    return os.environ.get(variable) or default


def log(*parts):
    print("[kameen]", *parts, file=sys.stderr, flush=True)


async def json_call(role, system, user, schema, max_tokens=2000, effort="low"):
    """One structured-output call. Returns a dict, or None on a refusal or an error."""
    request = dict(
        model=model(role), max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
    )
    trace(system, user)
    try:
        if role == "live":
            # Haiku 5.5: thinking can be switched off. It has no server-side refusal fallback.
            message = await client().messages.create(thinking={"type": "disabled"}, **request)
        else:
            # Sonnet 5.5 and Opus 5.5: thinking stays on; a declined request falls back server-side.
            message = await client().beta.messages.create(
                betas=["server-side-fallback-2026-07-01"], fallbacks="default", **request)
    except Exception as error:                     # background jobs must never break a turn
        log(f"{role} call failed:", repr(error))
        return None
    record(request["model"], message.usage)
    if message.stop_reason != "end_turn":
        log(f"{role} call stopped with", message.stop_reason)
        return None
    text = next((block.text for block in message.content if block.type == "text"), "")
    try:
        return json.loads(text)
    except ValueError:
        log(f"{role} call returned text that is not JSON")
        return None
