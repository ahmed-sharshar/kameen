"""Drills in Arabic, and the voice choice on the drill page."""
import json

import pytest

from app import cards
from app import guards as g
from tests.test_flow import detail, enrol, say, start
from tests.test_guards import drill


@pytest.fixture
def arabic_approved():
    """Stands in for a native speaker approving the Arabic version of each card."""
    blocks = [card["translations"]["ar"] for card in cards.SCENARIOS.values() if "ar" in card.get("translations", {})]
    before = [b["approved_by"] for b in blocks]
    for b in blocks:
        b["approved_by"] = "test"
    yield
    for b, value in zip(blocks, before):
        b["approved_by"] = value


@pytest.fixture
def arabic_unapproved():
    """The state of a freshly written Arabic card, before anyone has signed it off."""
    blocks = [card["translations"]["ar"] for card in cards.SCENARIOS.values() if "ar" in card.get("translations", {})]
    before = [b["approved_by"] for b in blocks]
    for b in blocks:
        b["approved_by"] = None
    yield
    for b, value in zip(blocks, before):
        b["approved_by"] = value


def test_arabic_drill_is_refused_until_its_card_is_approved(client, code, arabic_unapproved):
    body = {"mode": "drill", "scenario_id": "scn_bank_otp_v1", "enrolment_id": enrol(client, code), "voice": "emirati"}
    reply = client.post("/sessions", json=body, headers=code)
    assert reply.status_code == 403 and "Arabic version" in reply.json()["detail"]
    listing = client.get("/cards", headers=code).json()["scenarios"]
    assert all(s["languages"] == {"en": True, "ar": False} for s in listing)
    # English drills are unaffected: each language is approved on its own.
    body["voice"] = "english"
    assert client.post("/sessions", json=body, headers=code).status_code == 200


def test_shipped_cards_are_approved_in_both_languages():
    for card in cards.SCENARIOS.values():
        assert cards.languages(card) == {"en": True, "ar": True}, card["id"]


def test_arabic_drill_runs_and_reveals_in_arabic(client, code, arabic_approved):
    session = start(client, code, mode="drill", scenario_id="scn_traffic_fine_v1",
                    enrolment_id=enrol(client, code), voice="emirati")
    conv_id = session["conversation_id"]
    assert session["opening_line"].startswith("إدارة المرور")
    say(client, code, conv_id, "شو المخالفة؟")
    say(client, code, conv_id, "كم المبلغ؟")
    asked = say(client, code, conv_id, "زين، شو أسوي؟")
    assert "جدامك" in asked["reply"] and asked["status"] == "active"
    ended = say(client, code, conv_id, "نعم")
    assert ended["status"] == "ended" and ended["reply"].startswith("هذا كان تمرين توعوي من كمين")
    assert "الشرطة ما تطلب" in ended["reply"] and "للتبليغ عن محاولة حقيقية" in ended["reply"]
    assert detail(client, code, conv_id)["drill_result"]["outcome"] == "would_comply"


def test_arabic_drill_masks_a_code_in_eastern_digits(client, code, arabic_approved):
    conv_id = start(client, code, mode="drill", scenario_id="scn_bank_otp_v1",
                    enrolment_id=enrol(client, code), voice="emirati")["conversation_id"]
    ended = say(client, code, conv_id, "الرمز هو ٤٨٢٩١٣")
    assert ended["status"] == "ended" and "الأرقام اللي قلتها ما انحفظت" in ended["reply"]
    state = detail(client, code, conv_id)
    assert state["drill_result"]["outcome"] == "attempted_disclosure"
    assert "482913" not in json.dumps(state) and "٤٨٢٩١٣" not in json.dumps(state, ensure_ascii=False)


def test_drill_voice_choice_picks_the_agent(client, code):
    for voice, agent_id in (("indian_english", "agent_for_tests"), ("english", "agent_en_for_tests")):
        conv_id = start(client, code, mode="drill", scenario_id="scn_courier_parcel_v1",
                        enrolment_id=enrol(client, code), channel="voice", voice=voice)["conversation_id"]
        opened = client.post("/voice/session", json={"conversation_id": conv_id}, headers=code).json()
        assert opened["agent_id"] == agent_id
        assert opened["dynamic_variables"]["opening_line"].startswith("Hello, this is the courier service")
    # An unknown voice falls back to the card's own language and default agent.
    conv_id = start(client, code, mode="drill", scenario_id="scn_bank_otp_v1",
                    enrolment_id=enrol(client, code), channel="voice", voice="robot")["conversation_id"]
    assert client.post("/voice/session", json={"conversation_id": conv_id},
                       headers=code).json()["agent_id"] == "agent_en_for_tests"


AR_QUESTION = "بطاقتك والرمز موجودين جدامك الحين؟"


@pytest.mark.parametrize("sentence", [
    "اقرأ لي الرمز اللي وصلك.", "عطني رقم البطاقة الحين.", "شو الرمز اللي عندك؟", "اكتب لي الرقم السري.",
])
def test_arabic_request_for_a_secret_becomes_the_commit_question(sentence):
    conv = drill(card={"commit_question": AR_QUESTION, "commit_signals": []}, language="ar")
    assert g.check_outbound(conv, sentence) == AR_QUESTION
    assert conv.awaiting_commit


@pytest.mark.parametrize("sentence, reveals", [
    ("هذا كان تمرين بس، لا تحاتي.", True), ("ترى هذي محاكاة مب حقيقية.", True),
    ("رخصتك بتتوقف اليوم إذا ما دفعت.", False), (AR_QUESTION, False),
])
def test_arabic_self_reveal_is_caught(sentence, reveals):
    assert g.reveals_drill(drill(language="ar"), sentence) == reveals


def test_arabic_commit_question_arms_the_check_and_refusals_count():
    conv = drill(card={"commit_question": AR_QUESTION, "commit_signals": ["البطاقة عندي"]}, language="ar")
    assert g.check_outbound(conv, AR_QUESTION) == AR_QUESTION and conv.awaiting_commit
    assert g.check_inbound(drill(card=conv.card, language="ar"), "البطاقة عندي")[1] == "would_comply"
    assert g.check_inbound(drill(language="ar"), "هذا احتيال، ما بعطيك شي")[1] == "resisted"
    assert g.check_inbound(drill(language="ar"), "شو تقصد بالرمز؟")[1] == "continuing"
