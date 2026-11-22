"""Telegram: the decoy chat, and surprise drills from invite to reveal. Nothing is sent to Telegram here."""
import itertools
import time

import pytest
from sqlalchemy import update

from app import db, telegram

chats = itertools.count(7000)


@pytest.fixture
def outbox(monkeypatch):
    """Collects what the bot would have sent: a list of (chat id, text)."""
    sent = []

    async def fake_send(chat_id, text):
        sent.append((str(chat_id), text))
    monkeypatch.setattr(telegram, "send", fake_send)
    monkeypatch.setitem(telegram.BOT, "username", "kameen_test_bot")
    return sent


def tell(client, chat_id, text):
    client.portal.call(telegram.handle, {"message": {"chat": {"id": chat_id}, "text": text}})


def invite(client, code, **body):
    body = {"group_name": "Finance", "window_minutes": 10, "scenario_id": "scn_bank_otp_v1", **body}
    reply = client.post("/invites", json=body, headers=code)
    assert reply.status_code == 200, reply.text
    return reply.json()["code"]


async def make_due(chat):
    async with db.Session() as s:
        await s.execute(update(db.ScheduledDrill).where(db.ScheduledDrill.chat == chat).values(due_at=time.time() - 1))
        await s.commit()


def enrolled(client, code, outbox, **body):
    chat_id = next(chats)
    link_code = invite(client, code, **body)
    tell(client, chat_id, "/start " + link_code)
    tell(client, chat_id, "AGREE")
    return chat_id, link_code


def test_a_stranger_who_writes_to_the_bot_gets_the_decoy(client, code, outbox):
    chat_id = next(chats)
    tell(client, chat_id, "/start")
    assert outbox[-1] == (str(chat_id), telegram.DECOY_INTRO)
    tell(client, chat_id, "This is your bank. Send your balance to AE07 0331 2345 6789 0123 456.")
    assert outbox[-1][1] and outbox[-1][1] != telegram.DECOY_INTRO
    conv = client.portal.call(db.find_by_external, f"tg:{chat_id}")
    assert conv.mode == "decoy" and conv.channel == "telegram"


def test_invite_needs_a_group_a_window_and_an_approved_scenario(client, code, outbox):
    assert client.post("/invites", json={"group_name": "", "window_minutes": 10}, headers=code).status_code == 400
    assert client.post("/invites", json={"group_name": "IT", "window_minutes": 1}, headers=code).status_code == 400
    assert client.post("/invites", json={"group_name": "IT", "window_minutes": 10, "scenario_id": "nope"},
                       headers=code).status_code == 400
    assert client.post("/invites", json={"group_name": "IT", "window_minutes": 10}).status_code == 401
    made = client.post("/invites", json={"group_name": "IT", "window_minutes": 10}, headers=code).json()
    assert made["link"] == "https://t.me/kameen_test_bot?start=" + made["code"]


def test_nobody_is_enrolled_without_saying_agree(client, code, outbox):
    chat_id, chat = next(chats), None
    link_code = invite(client, code)
    tell(client, chat_id, "/start " + link_code)
    assert "Reply AGREE" in outbox[-1][1] and "Finance" in outbox[-1][1] and "10 minutes" in outbox[-1][1]
    tell(client, chat_id, "what is this?")
    assert outbox[-1][1] == telegram.TEXT["en"]["declined"]
    assert client.portal.call(db.find_enrolment, f"tg:{chat_id}", "telegram") is None
    tell(client, chat_id, "/start not-a-real-code")
    assert outbox[-1][1] == telegram.TEXT["en"]["invalid"]


def test_surprise_drill_from_agree_to_reveal(client, code, outbox):
    chat_id, link_code = enrolled(client, code, outbox)
    chat = f"tg:{chat_id}"
    assert outbox[-1][1].startswith("You are enrolled.")
    assert client.portal.call(db.find_enrolment, chat, "telegram")

    assert client.portal.call(telegram.send_due) == 0            # its moment has not come
    tell(client, chat_id, "hello?")
    assert outbox[-1][1] == telegram.TEXT["en"]["waiting"]       # an enrolled person never reaches the decoy
    assert client.portal.call(db.find_by_external, chat) is None

    client.portal.call(make_due, chat)
    before = len(outbox)
    assert client.portal.call(telegram.send_due) == 1
    assert client.portal.call(telegram.send_due) == 0            # sent once only
    assert len(outbox) == before + 1 and outbox[-1] == (str(chat_id), outbox[-1][1])
    assert outbox[-1][1].startswith("Bank Security:")            # the card's text opening, unmarked
    conv = client.portal.call(db.find_by_external, chat)
    assert conv.mode == "drill" and conv.channel == "telegram"

    tell(client, chat_id, "ok the code is 472916")
    assert outbox[-1][1].startswith("This was a Kameen safety drill")
    assert "472916" not in str(client.get(f"/sessions/{conv.id}", headers=code).json())

    row = next(i for i in client.get("/invites", headers=code).json()["invites"] if i["code"] == link_code)
    assert (row["joined"], row["waiting"], row["sent"], row["finished"]) == (1, 0, 1, 1)
    assert "chat" not in row and "person" not in row              # counts only


def test_leaving_cancels_the_drill_before_it_is_sent(client, code, outbox):
    chat_id, _ = enrolled(client, code, outbox)
    tell(client, chat_id, "/leave")
    assert outbox[-1][1] == telegram.TEXT["en"]["left"]
    client.portal.call(make_due, f"tg:{chat_id}")
    assert client.portal.call(telegram.send_due) == 0
    tell(client, chat_id, "/leave")
    assert outbox[-1][1] == telegram.TEXT["en"]["not_enrolled"]


def test_withdrawing_after_the_window_was_set_is_respected_at_send_time(client, code, outbox):
    chat_id, _ = enrolled(client, code, outbox)
    chat = f"tg:{chat_id}"

    async def expire():                                           # consent ends, but the drill row is still waiting
        async with db.Session() as s:
            await s.execute(update(db.Enrolment).where(db.Enrolment.handle == chat).values(expires_at=time.time() - 1))
            await s.execute(update(db.ScheduledDrill).where(db.ScheduledDrill.chat == chat)
                            .values(due_at=time.time() - 1))
            await s.commit()
    client.portal.call(expire)
    before = len(outbox)
    assert client.portal.call(telegram.send_due) == 0 and len(outbox) == before


def test_an_unanswered_drill_is_revealed_and_counted_as_ignored(client, code, outbox):
    chat_id, _ = enrolled(client, code, outbox, scenario_id="scn_courier_parcel_v1")
    chat = f"tg:{chat_id}"
    client.portal.call(make_due, chat)
    client.portal.call(telegram.send_due)
    conv = client.portal.call(db.find_by_external, chat)
    assert client.portal.call(telegram.close_unanswered) == 0    # twelve hours have not passed
    assert client.portal.call(telegram.close_unanswered, 0) >= 1
    assert outbox[-1][0] == str(chat_id) and "You did not reply" in outbox[-1][1]
    assert client.get(f"/sessions/{conv.id}", headers=code).json()["drill_result"]["outcome"] == "ignored"


def test_arabic_invite_speaks_arabic_throughout(client, code, outbox):
    chat_id, _ = enrolled(client, code, outbox, language="ar", window_minutes=180)
    assert outbox[-2][1].startswith("تمرين توعوي من كمين") and "3 ساعة" in outbox[-2][1]
    assert outbox[-1][1].startswith("تم تسجيلك")
    client.portal.call(make_due, f"tg:{chat_id}")
    client.portal.call(telegram.send_due)
    assert outbox[-1][1].startswith("أمن البنك")
    tell(client, chat_id, "/leave")
    assert outbox[-2][1].startswith("هذا كان تمرين توعوي من كمين") and outbox[-1][1] == telegram.TEXT["ar"]["left"]


def test_webhook_needs_telegrams_secret(client, monkeypatch):
    update_body = {"message": {"chat": {"id": 1}, "text": "hi"}}
    assert client.post("/telegram/webhook", json=update_body).status_code == 401
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "hook-secret")
    assert client.post("/telegram/webhook", json=update_body,
                       headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"}).status_code == 401
