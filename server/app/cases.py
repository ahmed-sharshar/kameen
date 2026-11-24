"""Simulated police-side case handoff.

This module is a DEMONSTRATION only. Nothing here talks to TAMM, UAE Pass or the Abu Dhabi Police
Aman service, and Kameen is not authorised to. It mirrors the shape of that real workflow — verify the
victim's identity (UAE Pass), file a cybercrime case (TAMM / Aman), send the citizen a case reference —
using synthetic records drawn from Kameen's own drills and awareness tests. The Emirates ID is invented,
the case reference is local, and the follow-up SMS is never sent: it is shown in the dashboard, clearly
marked as a simulation. If this were ever authorised for real, the mock steps below are where the real
UAE Pass OAuth and the real case API would slot in.
"""
import random
from datetime import datetime, timezone

from . import cards, db, notify

# "Fooled": the person was caught out (about to give a secret, or clicked the phishing link).
# Everything else is "not fooled" and needs no follow-up.
FOOLED = {"would_comply", "attempted_disclosure", "clicked"}

CHANNEL_LABEL = {"voice": "Phone call", "web": "Web / SMS", "telegram": "Telegram", "email": "Email",
                 "sms": "SMS"}


def _case_ref(seq):
    """A local, clearly-simulated case reference, shaped like an Aman reference."""
    return f"AMAN-SIM-{datetime.now(timezone.utc):%Y}-{int(seq):04d}"


def _mock_emirates_id(seed):
    """An INVENTED Emirates ID, as a stand-in for the identity UAE Pass would return. Never a real one."""
    rng = random.Random(str(seed))
    return f"784-{rng.randint(1960, 2006)}-{rng.randint(1000000, 9999999)}-{rng.randint(1, 9)}"


def scam_title(scenario_id):
    return (cards.scenario(scenario_id or "") or {}).get("title", scenario_id or "Unknown scam")


async def _open(person, email, phone, channel, scenario_id, outcome, source, group_name):
    """Opens a case for ANY drill or click. A 'fooled' case is emailed automatically to the awareness
    team; a 'not fooled' case is recorded and needs no action."""
    seq = await db.count_cases() + 1
    ref = _case_ref(seq)
    fooled = outcome in FOOLED
    case = {"case_ref": ref, "person": person, "email": email, "phone": phone, "channel": channel,
            "scam_type": scam_title(scenario_id), "scenario_id": scenario_id, "outcome": outcome,
            "source": source, "group_name": group_name, "emirates_id": _mock_emirates_id(ref)}
    await db.add_case(sms_text="", **case)
    if not fooled:
        await db.set_case_status(ref, "No action")
        return ref
    # Auto-email only for the default number. Any other case stays "Open" for a manual send to any
    # address from the Cases tab.
    if phone and phone == notify.auto_email_number():
        ok, _error = await notify.send_case_email(case, notify.alert_email())
        if ok:
            await db.set_case_emailed(ref, notify.alert_email())
    return ref


async def open_from_drill(conv, outcome):
    """Called after every drill is revealed: opens a case for the outcome, fooled or not."""
    enrol = await db.get_enrolment(conv.enrolment_id)
    person = (enrol.person if enrol else None) or "Unknown"
    group = (enrol.group_name if enrol else "") or ""
    # Only a voice drill carries a phone number (the number that was called); text drills carry none.
    phone = enrol.handle if (enrol and conv.channel == "voice" and enrol.handle) else None
    return await _open(person=person, email=None, phone=phone, channel=conv.channel,
                       scenario_id=conv.scenario_id, outcome=outcome, source="drill", group_name=group)


async def open_from_phish(target):
    """Called on the first click of a phishing-awareness link."""
    return await _open(person=target.name, email=target.email, phone=None, channel="email",
                       scenario_id=target.scenario_id, outcome="clicked", source="phishing", group_name="")
