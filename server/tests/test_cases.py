"""Simulated cases: a case is opened for every drill and every phishing click.

A "fooled" case (caught out) is emailed to the awareness team automatically; a "not fooled" case needs
no action. SMS was removed. The email sender is mocked here, so nothing actually sends.
"""
from types import SimpleNamespace

import pytest

from app import cases, notify, sessions

from .test_phish import flush, mailbox, make_campaign  # noqa: F401  (mailbox is a fixture used by name)


@pytest.fixture
def emails(monkeypatch):
    """Captures the case emails that would have been sent, instead of calling Resend."""
    sent = []

    async def fake_send(case):
        sent.append(case)
        return True, ""
    monkeypatch.setattr(notify, "send_case_email", fake_send)
    return sent


def cases_now(client, code):
    return client.get("/cases", headers=code).json()["cases"]


def find_case(client, code, **match):
    return next((c for c in cases_now(client, code) if all(c.get(k) == v for k, v in match.items())), None)


def test_cases_endpoint_needs_the_access_code(client):
    assert client.get("/cases").status_code == 401


def test_a_phishing_click_opens_and_emails_a_fooled_case(client, code, mailbox, emails):
    make_campaign(client, code, recipients=[{"name": "Dana Case", "email": "dana.case@example.com"}])
    flush(client)
    token = mailbox[0]["link"].rsplit("/", 1)[1]
    client.get(f"/t/{token}")

    case = find_case(client, code, email="dana.case@example.com")
    assert case is not None
    assert case["outcome"] == "clicked" and case["channel"] == "email"
    assert case["status"] == "Emailed"                                  # fooled -> auto-emailed
    assert any(c["case_ref"] == case["case_ref"] for c in emails)       # the email was sent


def test_an_at_risk_voice_drill_emails_the_case_with_the_phone(client, code, emails):
    phone = "+971500009999"
    enrolment_id = client.portal.call(sessions.enrol, phone, "Finance", phone, "operator", ["voice"])
    conv = SimpleNamespace(enrolment_id=enrolment_id, channel="voice", scenario_id="scn_bank_otp_v1")
    client.portal.call(cases.open_from_drill, conv, "attempted_disclosure")

    case = find_case(client, code, phone=phone)
    assert case is not None and case["channel"] == "voice" and case["status"] == "Emailed"
    assert any(c.get("phone") == phone for c in emails)


def test_a_not_fooled_drill_opens_a_case_but_sends_nothing(client, code, emails):
    conv = SimpleNamespace(enrolment_id=None, channel="web", scenario_id="scn_bank_otp_v1")
    client.portal.call(cases.open_from_drill, conv, "resisted")
    opened = [c for c in cases_now(client, code) if c["outcome"] == "resisted"]
    assert opened and all(c["status"] == "No action" for c in opened)   # recorded, no action
    assert emails == []                                                 # nothing emailed


def test_the_case_email_is_branded_never_police():
    case = {"case_ref": "AMAN-SIM-2026-0001", "person": "Test", "channel": "voice",
            "scam_type": "Bank security team", "outcome": "would_comply", "group_name": "Finance",
            "emirates_id": "784-1990-1234567-8", "email": None, "phone": "+971500000000"}
    text = notify.case_text(case).lower()
    assert "scamshield ai" in text and "simulation" in text and "not a real police case" in text
    assert not text.startswith("abu dhabi police")
