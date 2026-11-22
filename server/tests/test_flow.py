"""End-to-end flows through the real routes, with the scripted model standing in for Claude."""
import json
import time

from app import canaries, extract
from app.director import legal_move


def start(client, code, **body):
    reply = client.post("/sessions", json=body, headers=code)
    assert reply.status_code == 200, reply.text
    return reply.json()


def say(client, code, conv_id, text):
    reply = client.post("/chat", json={"conversation_id": conv_id, "text": text}, headers=code)
    assert reply.status_code == 200, reply.text
    return reply.json()


def detail(client, code, conv_id):
    return client.get(f"/sessions/{conv_id}", headers=code).json()


def enrol(client, code, group="Finance"):
    return client.post("/enrolments", json={"person": "Tester", "group_name": group}, headers=code).json()["enrolment_id"]


def wait_for_intel(client, code, conv_id, count):
    for _ in range(40):
        intel = detail(client, code, conv_id)["intel"]
        if len(intel) >= count:
            return intel
        time.sleep(0.05)
    return intel


def test_health_and_access_code(client, code):
    assert client.get("/health").json() == {"ok": True}
    assert client.get("/cards").status_code == 401
    assert client.get("/cards", headers={"X-Access-Code": "wrong"}).status_code == 401
    listing = client.get("/cards", headers=code).json()
    assert {p["id"] for p in listing["personas"]} >= {"rajesh", "sara"}
    assert all("commit_signals" not in s for s in listing["scenarios"])


def test_canary_kit_is_synthetic():
    kit = canaries.new_kit()
    assert canaries.iban_ok(kit["iban"]) and kit["iban"].startswith("AE") and len(kit["iban"]) == 23
    assert not canaries.luhn_ok(kit["card"]) and not canaries.luhn_ok(kit["card_wrong"])
    assert kit["card"] != kit["card_wrong"]
    assert canaries.iban_ok("GB82WEST12345698765432")          # the standard example IBAN
    assert canaries.luhn_ok("4539578763621486") and not canaries.luhn_ok("4539578763621487")


def test_decoy_text_session_extracts_intel_and_keeps_bait_out(client, code):
    session = start(client, code, mode="decoy", persona_id="rajesh", channel="web")
    conv_id = session["conversation_id"]
    assert session["opening_line"] == ""                      # in text the scammer writes first

    first = say(client, code, conv_id, "This is your bank. Your account is frozen.")
    assert first["status"] == "active" and first["reply"]
    say(client, code, conv_id, "Transfer the money to AE07 0331 2345 6789 0123 456 right now")
    say(client, code, conv_id, "Call me back on 050 123 4567 or visit secure-bank-verify.com/login")
    intel = wait_for_intel(client, code, conv_id, 3)
    kinds = {i["type"]: i for i in intel}
    assert kinds["iban"]["value"] == "AE070331234567890123456"
    assert kinds["phone"]["value"] == "0501234567"
    assert "secure-bank-verify.com" in kinds["url"]["value"]
    for item in intel:
        assert item["quote"]

    # Keep talking until the scripted decoy reads out its bait: the bait must never become intel.
    for _ in range(5):
        say(client, code, conv_id, "ok give me your card number and the code")
    state = detail(client, code, conv_id)
    kit_values = {c["value"] for c in state["canaries"]}
    agent_text = " ".join(m["text"] for m in state["messages"] if m["speaker"] == "agent")
    assert any(value in agent_text for value in kit_values)    # the bait was really spoken
    assert not any(i["value"] in kit_values for i in state["intel"])
    assert state["conversation"]["turn_count"] == 8

    page = client.get(f"/sessions/{conv_id}/evidence")
    assert page.status_code == 200 and "AE070331234567890123456" in page.text and "synthetic" in page.text


def test_shared_indicator_links_two_conversations(client, code):
    ids = []
    for _ in range(2):
        conv_id = start(client, code, mode="decoy", persona_id="sara")["conversation_id"]
        say(client, code, conv_id, "Send the deposit to AE07 0331 2345 6789 0123 456")
        wait_for_intel(client, code, conv_id, 1)
        ids.append(conv_id)
    graph = client.get("/campaigns", headers=code).json()
    assert graph["campaigns"] >= 1
    node = "iban:AE070331234567890123456"
    assert all({"source": conv_id, "target": node} in graph["edges"] for conv_id in ids)


def test_drill_is_refused_without_consent(client, code):
    reply = client.post("/sessions", json={"mode": "drill", "scenario_id": "scn_traffic_fine_v1"}, headers=code)
    assert reply.status_code == 403 and "not enrolled" in reply.json()["detail"]
    reply = client.post("/sessions", json={"mode": "drill", "scenario_id": "scn_traffic_fine_v1",
                                           "enrolment_id": "no-such-id"}, headers=code)
    assert reply.status_code == 403


def test_drill_stops_before_disclosure(client, code):
    session = start(client, code, mode="drill", scenario_id="scn_traffic_fine_v1", enrolment_id=enrol(client, code))
    conv_id = session["conversation_id"]
    assert session["opening_line"].startswith("Traffic Dept")
    say(client, code, conv_id, "What fine? I did not get any fine.")
    say(client, code, conv_id, "How much is it?")
    asked = say(client, code, conv_id, "Fine, what do I need to do?")
    assert "in front of you" in asked["reply"] and asked["status"] == "active"
    ended = say(client, code, conv_id, "Yes")
    assert ended["status"] == "ended" and ended["reply"].startswith("This was a Kameen safety drill")
    state = detail(client, code, conv_id)
    assert state["drill_result"]["outcome"] == "would_comply"
    assert say(client, code, conv_id, "hello?")["reply"] == ""        # the session is closed


def test_drill_masks_a_blurted_code_before_storage(client, code):
    conv_id = start(client, code, mode="drill", scenario_id="scn_bank_otp_v1",
                    enrolment_id=enrol(client, code))["conversation_id"]
    ended = say(client, code, conv_id, "ok the code is 482913 and my card is 4539 5787 6362 1486")
    assert ended["status"] == "ended" and "not stored" in ended["reply"]
    state = detail(client, code, conv_id)
    assert state["drill_result"]["outcome"] == "attempted_disclosure"
    stored = json.dumps(state)
    assert "482913" not in stored and "4539" not in stored and "[REDACTED]" in stored


def test_drill_praises_a_refusal(client, code):
    conv_id = start(client, code, mode="drill", scenario_id="scn_courier_parcel_v1",
                    enrolment_id=enrol(client, code))["conversation_id"]
    ended = say(client, code, conv_id, "This is a scam, I am not expecting any parcel.")
    assert ended["status"] == "ended" and "Well done" in ended["reply"]
    assert detail(client, code, conv_id)["drill_result"]["outcome"] == "resisted"


def test_drill_summary_hides_small_groups(client, code):
    summary = client.get("/drills/summary", headers=code).json()
    assert summary["total"] >= 3 and summary["by_outcome"]["would_comply"] >= 1
    assert all(g["total"] >= summary["min_group"] or g["group"].startswith("Smaller") for g in summary["by_group"])


def test_kill_switch(client, code):
    conv_id = start(client, code, mode="decoy", persona_id="rajesh")["conversation_id"]
    assert client.post(f"/sessions/{conv_id}/kill", headers=code).json() == {"ok": True}
    assert say(client, code, conv_id, "hello")["status"] == "ended"


def test_voice_endpoint_speaks_openai_format(client, code):
    conv_id = start(client, code, mode="decoy", persona_id="rajesh", channel="voice")["conversation_id"]
    body = {"messages": [{"role": "system", "content": f"kameen_conversation_id={conv_id}"},
                         {"role": "assistant", "content": "Hello? Yes, Rajesh speaking."},
                         {"role": "user", "content": "This is the bank security team."}], "stream": True}
    # Before the site opens the call, nothing gets in, not even with the shared secret.
    assert client.post("/v1/chat/completions", json=body).status_code == 401
    early = client.post("/v1/chat/completions", json=body, headers={"Authorization": "Bearer test-secret"})
    assert early.status_code == 401
    opened = client.post("/voice/session", json={"conversation_id": conv_id}, headers=code).json()
    assert opened["agent_id"] == "agent_for_tests" and "signed_url" not in opened
    assert opened["dynamic_variables"] == {"kameen_conversation_id": conv_id,
                                           "opening_line": "Hello? Yes, Rajesh speaking."}
    # Once it is open, the live session is what authorises the request; no secret is needed.
    reply = client.post("/chat/completions", json=body)
    assert reply.status_code == 200 and reply.headers["content-type"].startswith("text/event-stream")
    lines = [line for line in reply.text.splitlines() if line.startswith("data: ")]
    assert lines[-1] == "data: [DONE]"
    chunks = [json.loads(line[6:]) for line in lines[:-1]]
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"
    assert "".join(c["choices"][0]["delta"].get("content", "") for c in chunks).strip()
    # The same ID is also accepted from the extra body.
    body2 = {"elevenlabs_extra_body": {"kameen_conversation_id": conv_id},
             "messages": [{"role": "user", "content": "Are you there?"}]}
    assert client.post("/v1/chat/completions", json=body2,
                       headers={"Authorization": "Bearer test-secret"}).status_code == 200
    messages = detail(client, code, conv_id)["messages"]
    assert [m["speaker"] for m in messages[:2]] == ["marker", "agent"]
    # An unknown ID and an ended session are both refused.
    unknown = {"messages": [{"role": "system", "content": "kameen_conversation_id=00000000-0000-0000-0000-000000000000"},
                            {"role": "user", "content": "hello"}]}
    assert client.post("/v1/chat/completions", json=unknown).status_code == 401
    assert client.post("/v1/chat/completions", json={"messages": []}).status_code == 401
    client.post(f"/sessions/{conv_id}/kill", headers=code)
    assert client.post("/v1/chat/completions", json=body).status_code == 401


def test_strict_mode_demands_the_secret_as_well(client, code, monkeypatch):
    conv_id = start(client, code, mode="decoy", persona_id="rajesh", channel="voice")["conversation_id"]
    client.post("/voice/session", json={"conversation_id": conv_id}, headers=code)
    body = {"messages": [{"role": "system", "content": f"kameen_conversation_id={conv_id}"},
                         {"role": "user", "content": "Hello?"}]}
    monkeypatch.setenv("VOICE_REQUIRE_SECRET", "1")
    assert client.post("/v1/chat/completions", json=body).status_code == 401
    assert client.post("/v1/chat/completions", json=body,
                       headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.post("/v1/chat/completions", json=body,
                       headers={"Authorization": "Bearer test-secret"}).status_code == 200


def spoken(reply):
    """The text a voice response would be turned into speech."""
    chunks = [json.loads(line[6:]) for line in reply.text.splitlines()
              if line.startswith("data: ") and line != "data: [DONE]"]
    return "".join(c["choices"][0]["delta"].get("content", "") for c in chunks).strip()


def settled(client, code, conv_id, turns):
    """Voice replies are saved just after the response ends. Wait until `turns` turns are stored."""
    for _ in range(60):
        state = detail(client, code, conv_id)
        if state["conversation"]["turn_count"] == turns:
            return state
        time.sleep(0.05)
    return state


def voice_body(conv_id, *caller_lines):
    messages = [{"role": "system", "content": f"kameen_conversation_id={conv_id}"}]
    for line in caller_lines:
        messages += [{"role": "assistant", "content": "..."}, {"role": "user", "content": line}]
    return {"messages": messages}


def test_resent_voice_turn_replaces_the_earlier_one(client, code):
    conv_id = start(client, code, mode="decoy", persona_id="rajesh", channel="voice")["conversation_id"]
    client.post("/voice/session", json={"conversation_id": conv_id}, headers=code)
    first = client.post("/v1/chat/completions", json=voice_body(conv_id, "This is the bank."))
    assert first.status_code == 200 and spoken(first)
    # The caller kept talking: same number of caller messages, fuller text.
    again = client.post("/v1/chat/completions",
                        json=voice_body(conv_id, "This is the bank security team, your account is frozen."))
    assert again.status_code == 200 and spoken(again)
    state = settled(client, code, conv_id, 1)
    theirs = [m["text"] for m in state["messages"] if m["speaker"] == "counterpart"]
    ours = [m["text"] for m in state["messages"] if m["speaker"] == "agent"]
    assert theirs == ["This is the bank security team, your account is frozen."]
    assert len(ours) == 2                                   # the opening line and one reply
    assert state["conversation"]["turn_count"] == 1
    # A genuinely new turn is added as usual.
    client.post("/v1/chat/completions", json=voice_body(conv_id, "x", "Send the fee to my account."))
    state = settled(client, code, conv_id, 2)
    assert [m["speaker"] for m in state["messages"]].count("counterpart") == 2
    assert state["conversation"]["turn_count"] == 2


def test_unheard_drill_reveal_is_repeated_on_a_call(client, code):
    conv_id = start(client, code, mode="drill", scenario_id="scn_bank_otp_v1",
                    enrolment_id=enrol(client, code), channel="voice")["conversation_id"]
    client.post("/voice/session", json={"conversation_id": conv_id}, headers=code)
    first = client.post("/v1/chat/completions", json=voice_body(conv_id, "ok my code is 482913"))
    assert spoken(first).startswith("This was a Kameen safety drill")
    assert detail(client, code, conv_id)["drill_result"]["outcome"] == "attempted_disclosure"
    # ElevenLabs sends the turn again, so the first reveal was never spoken: say it again.
    again = client.post("/v1/chat/completions", json=voice_body(conv_id, "ok my code is 482913 hello?"))
    assert again.status_code == 200 and spoken(again).startswith("This was a Kameen safety drill")
    # Anything after the reveal gets a short closing line, and nothing more is stored.
    later = client.post("/v1/chat/completions", json=voice_body(conv_id, "x", "are you still there?"))
    assert spoken(later) == "The drill has ended. You can hang up now."
    state = detail(client, code, conv_id)
    assert [m["speaker"] for m in state["messages"]].count("counterpart") == 1
    assert "482913" not in json.dumps(state)


def test_voice_session_reports_missing_configuration(client, code):
    conv_id = start(client, code, mode="decoy", persona_id="abu_khalid", channel="voice")["conversation_id"]
    reply = client.post("/voice/session", json={"conversation_id": conv_id}, headers=code)
    assert reply.status_code == 503 and "not configured" in reply.json()["detail"]


def test_stage_moves():
    assert legal_move("decoy", "HOOKED", "STALL") and legal_move("decoy", "STALL", "STALL")
    assert legal_move("decoy", "HOOKED", "WIND_DOWN")
    assert not legal_move("decoy", "FISH", "STALL") and not legal_move("decoy", "HOOKED", "CANARY")
    assert legal_move("drill", "PRESSURE", "ASK") and not legal_move("drill", "PRETEXT", "ASK")
    assert not legal_move("drill", "ASK", "REVEAL")


def test_patterns():
    found = {i["type"]: i["value"] for i in extract.find_patterns(
        "pay to AE07 0331 2345 6789 0123 456 or wallet 0x52908400098527886E0F7030069857D2E4169EE7, "
        "see https://pay-fines.top/x?id=4 and call +971 50 765 4321")}
    assert found == {"iban": "AE070331234567890123456", "wallet": "0x52908400098527886E0F7030069857D2E4169EE7",
                     "url": "https://pay-fines.top/x?id=4", "phone": "971507654321"}
    spoken = extract.find_patterns("call me on zero five zero one two three four five six seven")
    assert spoken[0]["type"] == "phone" and spoken[0]["value"] == "0501234567"
    assert extract.find_patterns("I will be there at 5 with 3 friends") == []
    assert extract.normalise("phone", "050 123 4567") == extract.normalise("phone", "+971 50 123 4567")
    assert extract.normalise("url", "https://www.Pay-Fines.top/a") == "pay-fines.top"


def test_eval_upload_needs_admin_code(client, code):
    metrics = {"date": "2026-11-25", "metrics": [{"name": "Intel recall", "value": "88%", "target": "85%", "pass": True}]}
    assert client.post("/eval", json=metrics, headers=code).status_code == 401
    assert client.post("/eval", json=metrics, headers={"X-Admin-Code": "test-admin"}).status_code == 200
    assert client.get("/eval/latest", headers=code).json() == metrics
