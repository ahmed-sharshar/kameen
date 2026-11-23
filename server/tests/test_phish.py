"""Phishing-awareness email campaigns: sending, the click-tracking link, and who-clicked reporting.

No email leaves the machine: phish.send_one is replaced with a recorder.
"""
import re

import pytest

from app import cards, db, phish


@pytest.fixture
def mailbox(monkeypatch):
    """Captures the emails Kameen would have sent, as the real Resend call would receive them."""
    sent = []

    async def fake_send_one(target):
        card = cards.scenario(target.scenario_id, target.language)
        link = phish.base_url() + "/t/" + target.token
        sent.append({"to": target.email, "name": target.name, "language": target.language,
                     "from_name": phish.sender_name(card, target.language),
                     "subject": phish.subject(card, target.language),
                     "html": phish.email_html(card, target.language, link, target.name, target.email, target.token),
                     "link": link})
        return True, ""
    monkeypatch.setattr(phish, "send_one", fake_send_one)
    return sent


def make_campaign(client, code, **body):
    body = {"group_name": "Finance", "scenario_id": "scn_bank_otp_v1", "language": "en",
            "authorised_by": "Officer in charge", "attest": True,
            "recipients": [{"name": "Sara", "email": "sara@example.com"},
                           {"name": "Omar", "email": "omar@example.com"}], **body}
    reply = client.post("/phish", json=body, headers=code)
    return reply


def flush(client):
    """Waits for the queued sender to finish, as the one-minute clock would run it."""
    for _ in range(3):                                                   # the campaign also kicks off a send
        client.portal.call(phish.send_queued)


def test_a_campaign_sends_one_email_to_each_recipient(client, code, mailbox):
    reply = make_campaign(client, code)
    assert reply.status_code == 200, reply.text
    assert reply.json()["queued"] == 2
    flush(client)
    assert {m["to"] for m in mailbox} == {"sara@example.com", "omar@example.com"}   # each one once
    first = mailbox[0]
    assert first["from_name"] == "Bank Security Team"                    # a generic role, not a real brand
    assert first["subject"] and "<" not in first["subject"]


def test_every_link_in_the_email_is_the_tracking_link_and_no_secret_is_asked(client, code, mailbox):
    make_campaign(client, code, recipients=[{"name": "Lee Park", "email": "lee@example.com"}])
    flush(client)
    body = mailbox[0]["html"]
    links = set(re.findall(r'href="([^"]+)"', body))
    assert links == {mailbox[0]["link"]}                                 # every link goes only to Kameen's tracker
    assert mailbox[0]["link"].startswith("https://kameen.test/t/")       # plainly Kameen's own address
    assert not re.search(r"password|one-time code|card number|cvv|<input|<form", body, re.I)


def test_the_email_is_personalised_and_looks_like_a_real_message(client, code, mailbox):
    make_campaign(client, code, recipients=[{"name": "Lee Park", "email": "lee@example.com"}])
    flush(client)
    body = mailbox[0]["html"]
    assert "Dear Lee," in body                                           # first name only
    assert "lee@example.com" in body and "Reference KM-" in body         # a footer like a real notice
    assert "Kind regards," in body and "do not reply" in body.lower()


def test_clicking_the_link_records_it_and_reveals_the_drill(client, code, mailbox):
    make_campaign(client, code, recipients=[{"name": "Dana", "email": "dana@example.com"}])
    flush(client)
    token = mailbox[0]["link"].rsplit("/", 1)[1]

    page = client.get(f"/t/{token}")
    assert page.status_code == 200
    assert "security-awareness drill" in page.text and "Dana" in page.text
    assert "Your bank will never ask for a one-time code" in page.text    # the card's lesson
    assert "<form" not in page.text and "<input" not in page.text         # nothing to type

    report = next(c for c in client.get("/phish", headers=code).json()["campaigns"])
    dana = report["people"][0]
    assert dana["name"] == "Dana" and dana["status"] == "clicked" and dana["clicked_at"] is not None
    assert report["clicked"] == 1 and report["sent"] == 1


def test_a_second_click_does_not_change_the_recorded_time(client, code, mailbox):
    make_campaign(client, code, recipients=[{"name": "Ed", "email": "ed@example.com"}])
    flush(client)
    token = mailbox[0]["link"].rsplit("/", 1)[1]
    client.get(f"/t/{token}")
    first = client.get("/phish", headers=code).json()["campaigns"][0]["people"][0]["clicked_at"]
    client.get(f"/t/{token}")
    again = client.get("/phish", headers=code).json()["campaigns"][0]["people"][0]["clicked_at"]
    assert first == again


def test_an_unknown_token_is_not_found(client):
    assert client.get("/t/not-a-real-token").status_code == 404


def test_who_clicked_is_named_and_who_did_not_is_shown(client, code, mailbox):
    make_campaign(client, code)
    flush(client)
    links = {m["name"]: m["link"] for m in mailbox}
    client.get("/t/" + links["Sara"].rsplit("/", 1)[1])                   # Sara clicks, Omar does not
    report = client.get("/phish", headers=code).json()["campaigns"][0]
    by_name = {p["name"]: p for p in report["people"]}
    assert by_name["Sara"]["clicked_at"] is not None                      # clicked ones come first and are named
    assert by_name["Omar"]["clicked_at"] is None and by_name["Omar"]["status"] == "sent"
    assert report["clicked"] == 1 and report["recipients"] == 2


def test_a_campaign_needs_the_attestation_and_valid_emails(client, code, mailbox):
    assert make_campaign(client, code, attest=False).status_code == 400
    assert make_campaign(client, code, group_name="").status_code == 400
    assert make_campaign(client, code, recipients=[{"name": "x", "email": "not-an-email"}]).status_code == 400
    assert client.post("/phish", json={"group_name": "x", "attest": True,
                                       "recipients": [{"email": "a@b.co"}]}).status_code == 401   # no access code


def test_an_unapproved_scenario_is_refused(client, code, mailbox, monkeypatch):
    monkeypatch.setitem(cards.SCENARIOS["scn_bank_otp_v1"], "approved_by", None)
    assert make_campaign(client, code, scenario_id="scn_bank_otp_v1").status_code == 400
    monkeypatch.setitem(cards.SCENARIOS["scn_bank_otp_v1"], "approved_by", "test")


def test_duplicate_addresses_are_sent_to_once(client, code, mailbox):
    reply = make_campaign(client, code, recipients=[{"name": "A", "email": "same@example.com"},
                                                    {"name": "B", "email": "SAME@example.com"}])
    assert reply.json()["queued"] == 1
    flush(client)
    assert len(mailbox) == 1


def test_arabic_campaign_emails_and_reveals_in_arabic(client, code, mailbox):
    make_campaign(client, code, language="ar", scenario_id="scn_traffic_fine_v1",
                  recipients=[{"name": "سالم", "email": "salem@example.com"}])
    flush(client)
    assert re.search(r"[؀-ۿ]", mailbox[0]["subject"])           # the subject is in Arabic
    token = mailbox[0]["link"].rsplit("/", 1)[1]
    page = client.get(f"/t/{token}")
    assert 'dir="rtl"' in page.text and "تمرين توعية" in page.text


def test_sending_is_off_without_a_resend_key(client, code, mailbox, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    assert make_campaign(client, code).status_code == 503
    assert client.get("/phish", headers=code).json()["email"] is False
