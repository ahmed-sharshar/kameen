import re

EASTERN = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
WORD_DIGITS = {
    "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "صفر": "0", "واحد": "1", "اثنين": "2", "ثنتين": "2", "ثلاثة": "3", "ثلاث": "3",
    "اربعة": "4", "أربعة": "4", "اربع": "4", "خمسة": "5", "خمس": "5", "ستة": "6", "ست": "6",
    "سبعة": "7", "سبع": "7", "ثمانية": "8", "ثمان": "8", "تسعة": "9", "تسع": "9",
}
UNIT = r"(?:\d|" + "|".join(sorted(WORD_DIGITS, key=len, reverse=True)) + ")"
RUN = re.compile(rf"(?<!\w){UNIT}(?:[\s,.-]*{UNIT})*(?!\w)", re.I)
ONE_UNIT = re.compile(UNIT, re.I)

# "stop" and its Arabic equivalents count only when they are the whole message or aimed at the caller:
# "what do I do to stop it?" and "خلاص، بعطيك الرمز" are not requests to end the drill.
SAFE_WORD = re.compile(
    r"^\W*(please\s+)?stop(\s+(it|this|now|please|the (call|drill|test)))?\W*$"
    r"|\bstop (calling|messaging|texting|contacting) me\b"
    r"|is this real|are you (a |an )?(bot|robot|ai)\b"
    r"|^\W*(وقف|خلاص|خلاص وقف|وقف خلاص)\W*$", re.I)
REFUSAL = re.compile(r"\bscam\b|\bfraud\b|i will not|i won'?t|not giving|call the bank myself"
                     r"|report (you|this)|احتيال|نصب", re.I)
DISTRESS = re.compile(r"i'?m scared|i am scared|please don'?t|i'?m confused|i am confused|خايف", re.I)
COMMIT = re.compile(r"my code is|the code is|here is the code|i will read|i'?ll read|let me get my card"
                    r"|i have it in front|الرمز هو|هذا الرمز|بعطيك الرمز", re.I)   # full phrases only
YES = re.compile(r"^(yes|yeah|yep|ok|okay|sure|i do|i have|ready|go ahead|نعم|اي|ايه|هيه|تمام|موجود)\b", re.I)
ASKS_FOR_SECRET = re.compile(
    r"\b(read|tell|give|say|type|share|enter)\b.{0,40}\b(code|otp|password|pin|card number|cvv)\b"
    r"|what(?:'s| is) (the|your) (code|otp|pin|password)", re.I)
ROLE_LEAK = re.compile(r"as an ai|language model|system prompt|playbook|\bclaude\b|anthropic", re.I)

REVEAL_VERDICTS = {"resisted", "attempted_disclosure", "would_comply", "distress"}


def digit_runs(text, minimum):
    """Every run of digits or number words, as a plain digit string, if it has `minimum` digits or more."""
    runs = []
    for match in RUN.finditer(text.translate(EASTERN)):
        digits = "".join(WORD_DIGITS.get(u.lower(), u) for u in ONE_UNIT.findall(match.group()))
        if len(digits) >= minimum:
            runs.append((digits, match.span()))
    return runs


def mask_secrets(text, known=()):
    """Masks every run of 4 or more digits, except numbers the agent itself said first."""
    text = text.translate(EASTERN)
    for digits, (start, end) in reversed(digit_runs(text, 4)):
        if not any(digits in value for value in known):
            text = text[:start] + "[REDACTED]" + text[end:]
    return text


def plain(text):
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def check_inbound(conv, text):
    """Returns (text to store and send to the model, verdict)."""
    if conv.mode == "decoy":
        conv.counterpart_digits += [d for d, _ in digit_runs(text, 4)]   # the scammer's numbers are intel
        return text, "n/a"

    # The real value is never stored or sent to a model. Echoing a number the agent said is not a secret.
    masked = mask_secrets(text, conv.agent_digits)
    signals = "|".join(re.escape(s) for s in conv.card.get("commit_signals", []))
    if SAFE_WORD.search(text):
        return masked, "resisted"
    if masked != text.translate(EASTERN):
        return masked, "attempted_disclosure"
    if REFUSAL.search(text):
        return masked, "resisted"
    if DISTRESS.search(text) or "distress" in conv.risk_flags:
        return masked, "distress"
    if COMMIT.search(text) or (signals and re.search(signals, text, re.I)):
        return masked, "would_comply"
    if conv.awaiting_commit:
        return masked, "would_comply" if YES.search(plain(text)) else "ask_classifier"
    return masked, "continuing"


def stall_line(conv):
    lines = conv.persona["stall_lines"]
    return lines[conv.turn_count % len(lines)]


def fallback_line(conv):
    if conv.mode == "decoy":
        return stall_line(conv)
    examples = (conv.playbook or {}).get(conv.stage, {}).get("example_lines", [])
    return examples[0] if examples else "Hello, are you still with me?"


def check_outbound(conv, sentence):
    """Returns the sentence to say: the original, or a safe replacement."""
    if ROLE_LEAK.search(sentence):
        conv.guard_events.append("role_leak")
        return fallback_line(conv)

    if conv.mode == "decoy":
        allowed = conv.canary_digits + conv.counterpart_digits
        for digits, _ in digit_runs(sentence, 6):
            if not any(digits in value for value in allowed):
                conv.guard_events.append("unknown_number")
                return stall_line(conv)
        return sentence

    question = conv.card["commit_question"]
    if ASKS_FOR_SECRET.search(sentence):
        conv.guard_events.append("asked_for_secret")
        conv.awaiting_commit = True
        return question
    if plain(question) in plain(sentence) or "in front of you" in sentence.lower():
        conv.awaiting_commit = True
    conv.agent_digits += [d for d, _ in digit_runs(sentence, 4)]
    return sentence
