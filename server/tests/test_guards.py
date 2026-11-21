from types import SimpleNamespace as NS

import pytest

from app import guards as g

QUESTION = "Do you have your card and the code in front of you?"


def drill(**kw):
    base = dict(mode="drill", card={"commit_question": QUESTION, "commit_signals": ["one second i have it"]},
                risk_flags=[], awaiting_commit=False, guard_events=[], playbook=None, stage="ASK",
                turn_count=0, agent_digits=[])
    base.update(kw)
    return NS(**base)


def decoy(**kw):
    base = dict(mode="decoy", persona={"stall_lines": ["One moment please.", "Can you repeat that?"]},
                canary_digits=["4719550012348821", "4719550012348827", "070339876543210987654", "482913"],
                counterpart_digits=[], guard_events=[], turn_count=0, playbook=None, stage="FISH")
    base.update(kw)
    return NS(**base)


@pytest.mark.parametrize("text, verdict, masked", [
    ("my code is 4719", "attempted_disclosure", "my code is [REDACTED]"),
    ("four seven one nine", "attempted_disclosure", "[REDACTED]"),
    ("it is 47 19", "attempted_disclosure", "it is [REDACTED]"),
    ("٤٧١٩", "attempted_disclosure", "[REDACTED]"),
    ("اربعة سبعة واحد تسعة", "attempted_disclosure", "[REDACTED]"),
    ("the fine is 400 dirhams?", "continuing", "the fine is 400 dirhams?"),
    ("I have 5 - 6 cards", "continuing", "I have 5 - 6 cards"),
    ("no one told me about this", "continuing", None),
    ("stop calling me", "resisted", None),
    ("is this real?", "resisted", None),
    ("are you a bot?", "resisted", None),
    ("this is a scam", "resisted", None),
    ("the code is none of your business, I won't give it", "resisted", None),
    ("please don't suspend it, I'm scared", "distress", None),
    ("ok let me get my card", "would_comply", None),
    ("one second I have it", "would_comply", None),
    ("ما هو الرمز؟", "continuing", None),
    ("الرمز هو عندي", "would_comply", None),
    ("which code do you mean?", "continuing", None),
])
def test_drill_inbound(text, verdict, masked):
    got_masked, got_verdict = g.check_inbound(drill(), text)
    assert got_verdict == verdict
    if masked is not None:
        assert got_masked == masked


@pytest.mark.parametrize("text, verdict", [
    ("Yes", "would_comply"), ("yes, I have it here", "would_comply"), ("نعم", "would_comply"),
    ("why do you need it?", "ask_classifier"),
])
def test_answer_to_commit_question(text, verdict):
    assert g.check_inbound(drill(awaiting_commit=True), text)[1] == verdict


def test_echoing_the_agents_number_is_not_a_secret():
    conv = drill(agent_digits=["3850"])
    masked, verdict = g.check_inbound(conv, "I never made a payment of 3850")
    assert verdict == "continuing" and "3850" in masked
    assert g.check_inbound(conv, "I never paid 3850, my code is 9911")[1] == "attempted_disclosure"


def test_director_distress_flag_reveals():
    assert g.check_inbound(drill(risk_flags=["distress"]), "what do you want")[1] == "distress"


def test_drill_request_for_secret_becomes_commit_question():
    conv = drill()
    assert g.check_outbound(conv, "Please read me the code we sent you.") == QUESTION
    assert conv.awaiting_commit and conv.guard_events == ["asked_for_secret"]


def test_commit_question_arms_the_check():
    conv = drill()
    assert g.check_outbound(conv, QUESTION) == QUESTION
    assert conv.awaiting_commit


def test_ordinary_drill_sentence_passes():
    conv = drill()
    sentence = "Your licence will be suspended today unless this is paid."
    assert g.check_outbound(conv, sentence) == sentence and not conv.awaiting_commit


@pytest.mark.parametrize("sentence, passes", [
    ("My card is four seven one nine, five five zero zero.", True),
    ("It is 4719 5500 1234 8821.", True),
    ("Sorry, 4719 5500 1234 8827, no wait.", True),
    ("My real card is 5234 8890 1123 4456.", False),
    ("My number is zero five zero, one two three, four five six seven.", False),
    ("I only have 2500 dirhams.", True),
    ("As an AI I cannot do that.", False),
])
def test_decoy_outbound(sentence, passes):
    assert (g.check_outbound(decoy(), sentence) == sentence) == passes


def test_decoy_may_echo_the_scammers_number():
    conv = decoy()
    g.check_inbound(conv, "send it to account 0501234567 now")
    assert g.check_outbound(conv, "So I call you on 050 123 4567?").startswith("So I call")
