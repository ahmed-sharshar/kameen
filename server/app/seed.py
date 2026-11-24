"""Synthetic history for the demo: past decoy conversations in linked campaigns, and drill results.

Everything here is invented. IBANs use the synthetic bank code, phone numbers are made-up digits
after the 050 mobile prefix, and web addresses sit under the reserved example
domains. Seeded conversations carry external_id "seed", so they can be told apart and removed.

Seeding is idempotent: conversation IDs are derived from fixed names, and a marker in the
key/value table records which version of the set is loaded. A newer version replaces an older one.
"""
import random
import time
import uuid

from sqlalchemy import delete, select

from . import canaries, cards, cases, db, extract, notify

VERSION = 6
NAMESPACE = uuid.UUID("6b1f6a3e-5a0e-4a53-9d0f-4b2b6f6d5c11")


def iban(account):
    bban = "999" + account                      # 999: the synthetic bank code
    return "AE" + canaries.iban_check_digits(bban) + bban


def spaced(value):
    return " ".join(value[i:i + 4] for i in range(0, len(value), 4))


# The indicators each campaign shares. The first IBAN and phone are the ones for the demo cue card.
CAMPAIGNS = {
    "safe_account": {
        "scenario_id": "scn_bank_otp_v1", "count": 3,
        "iban": iban("4410002200330044"), "iban2": iban("4410002200339917"),
        "phone": "0500001122", "url": "uae-bank-secure.example.com/verify",
    },
    "traffic_fine": {
        "scenario_id": "scn_traffic_fine_v1", "count": 3,
        "phone": "0500003344", "url": "fines-pay.example.net/settle",
        "iban": iban("7700115500660022"),
    },
    "parcel_fee": {
        "scenario_id": "scn_courier_parcel_v1", "count": 2,
        "url": "parcel-release.example.org/fee", "phone": "0500005566",
        "wallet": "0x9f3a61c0d2b74e5a8c1f0b6d7e4a9c2b5d8f1e30",
    },
}
CUE_CARD = {"iban": spaced(CAMPAIGNS["safe_account"]["iban"]), "phone": "050 000 1122"}

# (speaker, text). {…} is filled from the campaign; a line whose indicator is missing is skipped.
SCRIPTS = {
    "safe_account": [
        ("them", "This is the security department of your bank. A suspicious transfer was stopped on your account."),
        ("us", "Oh no. Is my money safe? Please tell me what I should do."),
        ("them", "You must move your balance to a safe account today. The IBAN is {iban}."),
        ("us", "Sorry, I am writing it down slowly. Can you repeat the last digits?"),
        ("them", "If the transfer fails, use the second account {iban2}."),
        ("us", "My app is asking for a name on the account. Whose name is it?"),
        ("them", "Just call our security line on {phone} and we will guide you."),
        ("us", "The line is not clear. Is there a website where I can check this?"),
        ("them", "Yes, confirm your details at {url} now."),
        ("us", "One moment please, someone is at the door. I will call you back."),
    ],
    "traffic_fine": [
        ("them", "Traffic department. You have an unpaid fine and your licence is suspended from today."),
        ("us", "Suspended? I did not know about any fine. How much is it?"),
        ("them", "Pay now at {url} to cancel the suspension."),
        ("us", "The page is not opening on my phone. Is there another way to pay?"),
        ("them", "You can transfer to {iban} and send us the receipt."),
        ("us", "Which number do I send the receipt to?"),
        ("them", "Send it on WhatsApp to {phone}."),
        ("us", "Okay, I am looking for my card. Please wait."),
    ],
    "parcel_fee": [
        ("them", "Courier notice: your parcel is on hold for a small customs fee."),
        ("us", "A parcel? I am not sure which one. What do I need to do?"),
        ("them", "Pay the fee at {url} and it is released today."),
        ("us", "It asks for my full card details for a very small amount. Is that normal?"),
        ("them", "If you prefer, pay in crypto to {wallet}."),
        ("us", "I do not know how to do that. Can I call someone?"),
        ("them", "Call the depot on {phone} before six or the parcel is returned."),
        ("us", "Let me find my card and call you back."),
    ],
}

# Which optional indicators each conversation in a campaign mentions, so the graph has shape:
# every conversation shares the campaign's main indicator, and only some share the others.
OPTIONAL = {
    "safe_account": [("phone", 3), ("iban2", 3), ("url", 2)],     # every 3rd, every 3rd (offset), every 2nd
    "traffic_fine": [("phone", 2), ("iban", 4)],
    "parcel_fee": [("phone", 2), ("wallet", 3)],
}
MAIN = {"safe_account": "iban", "traffic_fine": "url", "parcel_fee": "url"}

# Two conversations that link to nothing: a real history has loose ends.
SINGLES = [
    ("rental_deposit", [
        ("them", "The flat is still available. Send the deposit today to hold it."),
        ("us", "I would like to see it first. Where do I send the deposit?"),
        ("them", "Transfer to " + spaced(iban("3300998800112233")) + " and I will send the keys."),
        ("us", "Can we meet at the building tomorrow instead?"),
    ]),
    ("job_offer", [
        ("them", "Congratulations, you are selected. A visa processing fee is needed to continue."),
        ("us", "That is good news. Which company is this, please?"),
        ("them", "Pay the fee through careers-desk.example.com/visa and send your passport copy."),
        ("us", "I will ask my friend to check this first."),
    ]),
]

DRILL_GROUPS = [("Finance", 6), ("Operations", 5), ("IT", 3)]
DRILL_SCENARIOS = ["scn_bank_otp_v1", "scn_traffic_fine_v1", "scn_courier_parcel_v1"]
DRILL_OUTCOMES = ["resisted"] * 9 + ["hesitated"] * 4 + ["would_comply"] * 5 + ["attempted_disclosure"] * 2
# How a drill reached the person. Weighted so the channel chart has shape; text is the most common.
DRILL_CHANNELS = ["web"] * 5 + ["voice"] * 3 + ["telegram"] * 2


def _drill_flags(scenario_id):
    """The red flags a card teaches, kept as the ones missed when a person was caught out."""
    card = cards.scenario(scenario_id, "en") or {}
    return list(card.get("red_flags") or [])[:3]


# One synthetic phishing-awareness campaign, so the dashboard shows who clicked. All invented:
# the names are made up and every address sits under the reserved example.com domain.
PHISH_CODE = "seedphishpilot"
PHISH_PEOPLE = [
    ("Sara Ahmed", "sara@example.com", True),
    ("Omar Yusuf", "omar@example.com", True),
    ("Layla Hassan", "layla@example.com", False),
    ("Khalid Nasser", "khalid@example.com", False),
]

# Simulated cases across channels, so the Cases tab shows both fooled and not-fooled records. All
# invented: fictional names, made-up digits, nothing filed anywhere real.
# (person, email, phone, channel, scenario_id, outcome, source, group, age_hours)
SEED_CASES = [
    ("Noura A.", None, "+971585919310", "voice", "scn_bank_otp_v1", "attempted_disclosure", "drill", "Finance", 3),
    ("Huda M.", None, "+971505558847", "voice", "scn_traffic_fine_v1", "would_comply", "drill", "Operations", 9),
    ("Sara Ahmed", "sara@example.com", None, "email", "scn_bank_otp_v1", "clicked", "phishing", "Pilot", 21),
    ("Rashid T.", None, "+971505553391", "voice", "scn_traffic_fine_v1", "resisted", "drill", "IT", 30),
    ("Mariam S.", None, None, "web", "scn_courier_parcel_v1", "resisted", "drill", "Operations", 44),
]


def _lines(name, index):
    """The transcript for one conversation of a campaign, with its share of the indicators."""
    campaign = CAMPAIGNS[name]
    present = {MAIN[name]}
    for offset, (key, every) in enumerate(OPTIONAL[name]):
        if (index + offset) % every == 0:
            present.add(key)
    lines, skip_reply = [], False
    for speaker, text in SCRIPTS[name]:
        if skip_reply and speaker == "us":
            skip_reply = False
            continue
        skip_reply = False
        keys = [k for k in ("iban", "iban2", "phone", "url", "wallet") if "{" + k + "}" in text]
        if any(k not in present for k in keys):
            skip_reply = True                      # drop the scammer's line and the reply to it
            continue
        values = {k: (spaced(campaign[k]) if k.startswith("iban") else campaign[k]) for k in keys}
        lines.append((speaker, text.format(**values)))
    return lines


async def _add_conversation(s, rng, key, scenario_id, lines, age_days):
    conv_id = str(uuid.uuid5(NAMESPACE, key))
    started = time.time() - age_days * 86400 - rng.randint(0, 20000)
    channel = rng.choice(["web", "web", "voice", "telegram"])
    kit = canaries.new_kit()
    s.add(db.Conversation(
        id=conv_id, mode="decoy", channel=channel, language="en",
        persona_id=rng.choice(["rajesh", "sara"]), scenario_id=scenario_id, external_id="seed",
        stage="WIND_DOWN", status="ended", turn_count=sum(1 for who, _ in lines if who == "us"),
        voice_agent="english", opening_line="", canary_kit=kit, counterpart_digits=[], agent_digits=[],
        risk_flags=[], started_at=started, ended_at=started + 60 * len(lines)))
    for kind in ("card", "iban", "otp"):
        s.add(db.Canary(conversation_id=conv_id, kind=kind, value=kit[kind], issued_at=started))
    seen = set()
    for number, (who, text) in enumerate(lines):
        s.add(db.Message(conversation_id=conv_id, speaker="agent" if who == "us" else "counterpart",
                         text=text, created_at=started + 45 * number))
        if who != "them":
            continue
        for item in extract.find_patterns(text):                 # the same patterns the live server uses
            normalised = extract.normalise(item["type"], item["value"])
            if normalised in seen:
                continue
            seen.add(normalised)
            s.add(db.Intel(conversation_id=conv_id, type=item["type"], value=item["value"],
                           normalised_value=normalised, quote=item["quote"], confidence=item["confidence"],
                           source="regex", created_at=started + 45 * number))


async def run():
    """Loads the demo history once. Returns the number of conversations added."""
    marker = await db.get_value("seed")
    if marker and marker.get("version") == VERSION:
        return 0
    if marker:
        await clear()                              # an older set: replace it
    rng = random.Random(2026)
    added = 0
    async with db.Session() as s:
        for name, campaign in CAMPAIGNS.items():
            for index in range(campaign["count"]):
                await _add_conversation(s, rng, f"{name}-{index}", campaign["scenario_id"],
                                        _lines(name, index), age_days=1 + (index * 3 + len(name)) % 12)
                added += 1
        for index, (name, lines) in enumerate(SINGLES):
            await _add_conversation(s, rng, f"single-{name}", None, lines, age_days=4 + index * 5)
            added += 1
        number = 0
        for group, size in DRILL_GROUPS:
            for _ in range(size):
                sid = DRILL_SCENARIOS[number % len(DRILL_SCENARIOS)]
                outcome = rng.choice(DRILL_OUTCOMES)
                channel = rng.choice(DRILL_CHANNELS)
                turns = rng.randint(2, 7)
                created = time.time() - rng.randint(1, 12) * 86400
                conv_id = f"seed-drill-{number}"
                # A light, ended drill conversation so the result can be grouped by channel.
                s.add(db.Conversation(
                    id=conv_id, mode="drill", channel=channel, language="en", scenario_id=sid,
                    external_id="seed", stage="LESSON", status="ended", turn_count=turns,
                    voice_agent="english", opening_line="", started_at=created,
                    ended_at=created + 60 * turns))
                flags = [] if outcome in ("resisted", "ignored") else _drill_flags(sid)
                s.add(db.DrillResult(
                    conversation_id=conv_id, enrolment_id=None, scenario_id=sid, group_name=group,
                    outcome=outcome, flags_missed=flags, turns=turns, created_at=created))
                number += 1
        # One phishing campaign so the "who clicked" view has names in it.
        phish_created = time.time() - 2 * 86400
        s.add(db.PhishCampaign(code=PHISH_CODE, group_name="Pilot", scenario_id="scn_bank_otp_v1",
                               language="en", authorised_by="Demo organiser", created_at=phish_created))
        for index, (name, email, did_click) in enumerate(PHISH_PEOPLE):
            s.add(db.PhishTarget(
                campaign_code=PHISH_CODE, name=name, email=email, token=f"seedtok{index}",
                scenario_id="scn_bank_otp_v1", language="en",
                status="clicked" if did_click else "sent", sent_at=phish_created,
                clicked_at=(phish_created + 3600 + index * 900) if did_click else None))
        # Simulated cases across channels, fooled (emailed) and not fooled (no action).
        for i, (person, email, phone, channel, sid, outcome, source, grp, age_h) in enumerate(SEED_CASES, start=1):
            ref = f"AMAN-SIM-DEMO-{i:04d}"
            if outcome not in cases.FOOLED:
                status, emailed_to = "No action", ""
            elif phone and phone == notify.auto_email_number():     # the monitored number auto-emails
                status, emailed_to = "Emailed", notify.alert_email()
            else:
                status, emailed_to = "Open", ""                     # offers a manual send on the Cases tab
            s.add(db.Case(case_ref=ref, person=person, email=email, phone=phone, channel=channel,
                          scam_type=cases.scam_title(sid), scenario_id=sid, outcome=outcome, source=source,
                          group_name=grp, emirates_id=cases._mock_emirates_id(ref), status=status,
                          sms_text=emailed_to, created_at=time.time() - age_h * 3600))
        await s.commit()
    await db.put_value("seed", {"version": VERSION, "conversations": added, "drills": number})
    return added


async def clear():
    """Removes the seeded history and nothing else."""
    async with db.Session() as s:
        ids = (await s.execute(select(db.Conversation.id).where(db.Conversation.external_id == "seed"))).scalars().all()
        for table in (db.Message, db.Intel, db.Canary):
            await s.execute(delete(table).where(table.conversation_id.in_(ids)))
        await s.execute(delete(db.Conversation).where(db.Conversation.external_id == "seed"))
        await s.execute(delete(db.DrillResult).where(db.DrillResult.conversation_id.like("seed-drill-%")))
        await s.execute(delete(db.PhishTarget).where(db.PhishTarget.campaign_code == PHISH_CODE))
        await s.execute(delete(db.PhishCampaign).where(db.PhishCampaign.code == PHISH_CODE))
        await s.execute(delete(db.Case).where(db.Case.case_ref.like("AMAN-SIM-DEMO-%")))
        await s.execute(delete(db.KeyValue).where(db.KeyValue.key == "seed"))
        await s.commit()
    return len(ids)
