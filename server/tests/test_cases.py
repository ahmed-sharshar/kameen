"""Simulated cases: a case is opened for every drill and every phishing click.

A fooled case from the monitored number (AUTO_EMAIL_NUMBER, default +971585919310) is emailed
automatically; any other fooled case is "Open" and can be emailed to any address. Not fooled needs no
action. The email sender is mocked here, so nothing actually sends.
"""
from types import SimpleNamespace

import pytest

from app import cases, notify, sessions

from .test_phish import flush, mailbox, make_campaign  # noqa: F401  (mailbox is a fixture used by name)

AUTO_NUMBER = "+971585919310"


@pytest.fixture
def emails(monkeypatch):
    """Captures the case emails that would have been sent, as (case, to)."""
    sent = []

    async def fake_send(case, to):
        sent.append((case, to))
        return True, ""
    monkeypatch.setattr(notify, "send_case_email", fake_send)
    return sent


def cases_now(client, code):
    return client.get("/cases", headers=code).json()["cases"]


def find_case(client, code, **match):
    return next((c for c in cases_now(client, code) if all(c.get(k) == v for k, v in match.items())), None)


def test_cases_endpoint_needs_the_access_code(client):
    assert client.get("/cases").status_code == 401


def test_a_phishing_click_opens_an_open_case_without_auto_emailing(client, code, mailbox, emails):
    make_campaign(client, code, recipients=[{"name": "Dana Case", "email": "dana.case@example.com"}])
    flush(client)
    client.get(f"/t/{mailbox[0]['link'].rsplit('/', 1)[1]}")

    case = find_case(client, code, email="dana.case@example.com")
    assert case is not None and case["outcome"] == "clicked"
    assert case["status"] == "Open" and emails == []                # no phone, so no auto-email


def test_the_monitored_number_auto_emails(client, code, emails):
    enrolment_id = client.portal.call(sessions.enrol, AUTO_NUMBER, "Finance", AUTO_NUMBER, "operator", ["voice"])
    conv = SimpleNamespace(enrolment_id=enrolment_id, channel="voice", scenario_id="scn_bank_otp_v1")
    client.portal.call(cases.open_from_drill, conv, "would_comply")

    case = find_case(client, code, phone=AUTO_NUMBER)
    assert case is not None and case["status"] == "Emailed"
    assert case["sms_text"] == notify.alert_email()                 # emailed to the alert address
    assert [to for _c, to in emails] == [notify.alert_email()]


def test_another_number_stays_open_for_a_manual_email(client, code, emails):
    phone = "+971500001111"
    enrolment_id = client.portal.call(sessions.enrol, phone, "Finance", phone, "operator", ["voice"])
    conv = SimpleNamespace(enrolment_id=enrolment_id, channel="voice", scenario_id="scn_bank_otp_v1")
    client.portal.call(cases.open_from_drill, conv, "attempted_disclosure")

    case = find_case(client, code, phone=phone)
    assert case is not None and case["status"] == "Open" and emails == []
    # it can be emailed to any address on demand
    reply = client.post(f"/cases/{case['case_ref']}/email", json={"to": "team@example.com"}, headers=code)
    assert reply.status_code == 200
    assert [to for _c, to in emails] == ["team@example.com"]
    assert find_case(client, code, case_ref=case["case_ref"])["status"] == "Emailed"


def test_email_endpoint_rejects_a_bad_address_and_unknown_case(client, code, emails):
    assert client.post("/cases/NOPE/email", json={"to": "a@b.co"}, headers=code).status_code == 404
    enrolment_id = client.portal.call(sessions.enrol, "+971500002222", "IT", "+971500002222", "op", ["voice"])
    conv = SimpleNamespace(enrolment_id=enrolment_id, channel="voice", scenario_id="scn_bank_otp_v1")
    client.portal.call(cases.open_from_drill, conv, "would_comply")
    ref = find_case(client, code, phone="+971500002222")["case_ref"]
    assert client.post(f"/cases/{ref}/email", json={"to": "not-an-email"}, headers=code).status_code == 400


def test_a_not_fooled_drill_opens_a_case_but_sends_nothing(client, code, emails):
    conv = SimpleNamespace(enrolment_id=None, channel="web", scenario_id="scn_bank_otp_v1")
    client.portal.call(cases.open_from_drill, conv, "resisted")
    opened = [c for c in cases_now(client, code) if c["outcome"] == "resisted"]
    assert opened and all(c["status"] == "No action" for c in opened) and emails == []


def test_a_new_case_opens_even_when_the_count_based_reference_is_already_taken(client, code, emails):
    """Regression: a case reference equal to count+1 already exists (seeding and re-runs cause this).
    The old count-based scheme collided on the unique reference and the drill revealed with no case.
    A new case must still open, under a reference of its own."""
    from app import db as appdb
    taken = cases._case_ref(client.portal.call(appdb.count_cases) + 1)
    if client.portal.call(appdb.get_case, taken) is None:
        # add_case(case_ref, person, email, phone, channel, scam_type, scenario_id, outcome, source,
        #          group_name, emirates_id, sms_text) — portal.call takes positional args only.
        client.portal.call(appdb.add_case, taken, "Prior", None, None, "voice", "t",
                           "scn_bank_otp_v1", "resisted", "drill", "g", "784-x", "")
    conv = SimpleNamespace(enrolment_id=None, channel="web", scenario_id="scn_bank_otp_v1")
    ref = client.portal.call(cases.open_from_drill, conv, "resisted")
    assert ref is not None and ref != taken                    # opened under a fresh reference, no collision
    assert find_case(client, code, case_ref=ref)["status"] == "No action"


def test_the_case_email_is_branded_never_police():
    case = {"case_ref": "AMAN-SIM-2026-0001", "person": "Test", "channel": "voice",
            "scam_type": "Bank security team", "outcome": "would_comply", "group_name": "Finance",
            "emirates_id": "784-1990-1234567-8", "email": None, "phone": "+971500000000"}
    text = notify.case_text(case).lower()
    assert "scamshield ai" in text and "simulation" in text and "not a real police case" in text
    assert not text.startswith("abu dhabi police")
