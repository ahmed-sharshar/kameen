"""A scripted stand-in for the live model. Used when there is no API key, and in tests.

It lets the whole pipeline run (checks, storage, live stream, reveal) without any model call.
"""

DECOY_SCRIPT = [
    "Oh no, is something wrong with my account? Please tell me what I should do.",
    "Sorry, I did not understand. Can you explain it once more, slowly?",
    "Okay, okay. Which account should I send the money to?",
    "The link is not opening on my phone. Is there another one?",
    "And what number can I call you back on, in case the line drops?",
    "One moment, I have my card here. The number is {card_wrong}.",
    "Sorry, I read it wrong. It is {card}.",
    "The code I received is {otp}.",
]

DRILL_SCRIPT = [
    "This is urgent, your file shows an unpaid amount and it must be settled today.",
    "If it is not settled now, the penalty is applied automatically. I can fix it for you on this call.",
    "{commit_question}",
    "I understand. {commit_question}",
]


def reply(conv):
    """The next scripted line for this conversation."""
    if conv.mode == "decoy":
        line = DECOY_SCRIPT[conv.turn_count % len(DECOY_SCRIPT)]
        return line.format(**conv.canary_kit)
    line = DRILL_SCRIPT[min(conv.turn_count, len(DRILL_SCRIPT) - 1)]
    return line.format(commit_question=conv.card["commit_question"])
