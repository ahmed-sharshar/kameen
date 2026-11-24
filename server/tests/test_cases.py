"""Simulated police cases: opened when a drill catches someone out or a phishing link is clicked.

Everything here is synthetic. Nothing is filed to TAMM, UAE Pass or Aman, and no SMS is ever sent.
The session-scoped client shares one database, so these tests match cases by a unique email or phone
rather than by an absolute count.
"""
from types import SimpleNamespace

from app import cases, notify, sessions

from .test_phish import flush, mailbox, make_campaign  # noqa: F401  (mailbox is a fixture used by name)


def cases_now(client, code):
    return client.get("/cases", headers=code).json()["cases"]


def find_case(client, code, **match):
    return next((c for c in cases_now(client, code) if all(c.get(k) == v for k, v in match.items())), None)


def test_cases_endpoint_needs_the_access_code(client):
    assert client.get("/cases").status_code == 401


def test_a_phishing_click_opens_a_simulated_case(client, code, mailbox):
    make_campaign(client, code, recipients=[{"name": "Dana Case", "email": "dana.case@example.com"}])
    flush(client)
    token = mailbox[0]["link"].rsplit("/", 1)[1]
    assert find_case(client, code, email="dana.case@example.com") is None   # no case until the click
    client.get(f"/t/{token}")

    case = find_case(client, code, email="dana.case@example.com")
    assert case is not None
    assert case["person"] == "Dana Case" and case["channel"] == "email"
    assert case["source"] == "phishing" and case["outcome"] == "clicked"
    assert case["case_ref"].startswith("AMAN-SIM-") and case["emirates_id"].startswith("784-")
    # The stored message is the honest, project-branded notification, never a police impersonation.
    assert "ScamShield AI" in case["sms_text"] and "not a real police case" in case["sms_text"]


def test_a_second_click_does_not_open_a_second_case(client, code, mailbox):
    make_campaign(client, code, recipients=[{"name": "Ed Case", "email": "ed.case@example.com"}])
    flush(client)
    token = mailbox[0]["link"].rsplit("/", 1)[1]
    client.get(f"/t/{token}")
    client.get(f"/t/{token}")
    assert len([c for c in cases_now(client, code) if c["email"] == "ed.case@example.com"]) == 1


def test_an_at_risk_voice_drill_opens_a_case_with_the_phone_number(client, code):
    phone = "+971500009999"
    enrolment_id = client.portal.call(sessions.enrol, phone, "Finance", phone, "operator", ["voice"])
    conv = SimpleNamespace(enrolment_id=enrolment_id, channel="voice", scenario_id="scn_bank_otp_v1")
    client.portal.call(cases.open_from_drill, conv, "attempted_disclosure")

    case = find_case(client, code, phone=phone)
    assert case is not None
    assert case["channel"] == "voice" and case["source"] == "drill" and case["email"] is None


def test_a_resisted_drill_opens_no_case(client, code):
    before = len(cases_now(client, code))
    conv = SimpleNamespace(enrolment_id=None, channel="web", scenario_id="scn_bank_otp_v1")
    client.portal.call(cases.open_from_drill, conv, "resisted")
    assert len(cases_now(client, code)) == before                           # resisting is not a case


def test_the_notification_message_is_branded_never_police(client):
    msg = notify.message_text("AMAN-SIM-2026-0001")
    assert "ScamShield AI" in msg and "awareness simulation" in msg and "not a real police case" in msg
    assert not msg.lower().startswith("abu dhabi police")                   # never claims to BE the police


def test_notify_needs_attestation_then_sends_and_marks_the_case(client, code, mailbox, monkeypatch):
    make_campaign(client, code, recipients=[{"name": "Reem Case", "email": "reem.case@example.com"}])
    flush(client)
    client.get(f"/t/{mailbox[0]['link'].rsplit('/', 1)[1]}")
    ref = find_case(client, code, email="reem.case@example.com")["case_ref"]

    sent = []
    async def fake_notify(to, case_ref):
        sent.append((to, case_ref))
        return True, ""
    monkeypatch.setattr(notify, "notify", fake_notify)

    assert client.post(f"/cases/{ref}/notify", json={"to": "+971500000000"}, headers=code).status_code == 400
    reply = client.post(f"/cases/{ref}/notify", json={"to": "+971500000000", "attest": True}, headers=code)
    assert reply.status_code == 200 and reply.json()["channel"] == "sms"
    assert sent == [("+971500000000", ref)]
    assert find_case(client, code, case_ref=ref)["status"] == "Notified"


def test_notify_unknown_case_is_404(client, code):
    assert client.post("/cases/NOPE/notify", json={"to": "x@y.co", "attest": True}, headers=code).status_code == 404
