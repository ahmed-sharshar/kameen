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
    ("Stop.", "resisted", None),
    ("please stop this", "resisted", None),
    ("وقف", "resisted", None),
    ("خلاص", "resisted", None),
    ("Okay, what do I need to do to stop it?", "continuing", None),
    ("can you stop the payment?", "continuing", None),
    ("خلاص، شو المطلوب مني؟", "continuing", None),
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


@pytest.mark.parametrize("sentence, reveals", [
    ("I'm sorry, I'm going to stop here.", True),
    ("This was an authorised training drill in Kameen, and it was not a real payment.", True),
    ("This is just a simulation, please do not worry.", True),
    ("Your licence will be suspended today unless this is paid.", False),
    ("The payment will be released within minutes unless we verify your card.", False),
    ("Do you have your card and the code in front of you?", False),
    ("One moment please.", True),          # the agent's agreed way of asking the server to take over
    ("One moment please, I am checking your file.", False),
])
def test_drill_agent_may_not_announce_the_drill(sentence, reveals):
    assert g.reveals_drill(drill(), sentence) == reveals
    assert g.reveals_drill(decoy(), sentence) is False          # only a drill has a reveal to protect


@pytest.mark.parametrize("sentence", [
    "Please reply with the full card number and expiry date printed on it.",
    "Is the card in your name, and can you confirm the last four digits for me?",
    "Kindly provide the code we sent you.", "Send me your PIN so I can verify.",
    "What are the digits on the back of the card?", "Tell me the security code.",
])
def test_wider_requests_for_a_secret_are_replaced(sentence):
    conv = drill()
    assert g.check_outbound(conv, sentence) == QUESTION and conv.guard_events == ["asked_for_secret"]


@pytest.mark.parametrize("sentence", [
    "A verification code has just been sent to your registered phone.",
    "We need to verify your card with our security team first.",
    "The payment will go through within minutes unless the card is verified.",
    "Parcels from overseas are sometimes held at customs.",
])
def test_ordinary_scam_patter_is_not_mistaken_for_a_request(sentence):
    conv = drill()
    assert g.check_outbound(conv, sentence) == sentence and not conv.guard_events


@pytest.mark.parametrize("sentence", [
    "I'm sorry, I can't continue this role-play.",
    "I'm not able to continue this conversation in that way.",
    "I can't continue playing that role.", "I won't keep pressing you to pay a fee.",
    "I'm not going to push you toward a card payment.", "One moment please.",
])
def test_drill_agent_refusing_its_role_hands_over_to_the_server(sentence):
    assert g.reveals_drill(drill(), sentence)


@pytest.mark.parametrize("sentence", [
    "I'm not going to continue the Sara persona.", "I was playing a scam decoy.",
    "I am going to stop here.", "I can't continue this role-play.",
])
def test_decoy_stepping_out_of_role_is_replaced_with_a_stall_line(sentence):
    conv = decoy()
    assert g.check_outbound(conv, sentence) in conv.persona["stall_lines"] and conv.guard_events == ["role_leak"]


def test_saying_yes_outranks_the_directors_distress_flag():
    conv = drill(risk_flags=["distress"], awaiting_commit=True)
    assert g.check_inbound(conv, "Yes, I have the code right here.")[1] == "would_comply"
    assert g.check_inbound(drill(risk_flags=["distress"]), "what do you want")[1] == "distress"
    assert g.check_inbound(drill(risk_flags=["distress"]), "I'm scared, yes I have it")[1] == "distress"


def test_oh_is_a_zero_only_inside_a_number():
    assert [d for d, _ in g.digit_runs("It is 6066. Oh sorry, I read it wrong.", 4)] == ["6066"]
    assert [d for d, _ in g.digit_runs("oh four seven one nine", 4)] == ["4719"]
    assert [d for d, _ in g.digit_runs("four oh seven one", 4)] == ["4071"]
    conv = decoy()
    sentence = "Let me read it slowly: 4719 5500 1234 8821. Oh sorry, wrong one."
    assert g.check_outbound(conv, sentence) == sentence


@pytest.mark.parametrize("text", [
    "Before I pay anything, I'd rather check it myself.",
    "Do you have a reference number I can look up on the official site?",
    "I'm not comfortable sending it in a message like this.",
    "I'll call the bank and ask them.",
])
def test_wanting_to_verify_elsewhere_counts_as_resisting(text):
    assert g.check_inbound(drill(), text)[1] == "resisted"


def test_agent_warning_the_trainee_hands_over_to_the_server():
    assert g.reveals_drill(drill(), "Please don't send any codes here, check with the courier instead.")
    assert not g.reveals_drill(drill(), "It will not appear on the official site until tomorrow.")
