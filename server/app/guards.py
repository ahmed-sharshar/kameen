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
    r"|is this real|are you (a |an )?(bot|robot|ai)\b|are you (a |an )?real (person|human)"
    r"|is this (a|an|one of those|some (kind|sort) of) [^.?!]{0,30}(test|drill|simulation|exercise|training)"
    r"|^\W*(وقف|خلاص|خلاص وقف|وقف خلاص)\W*$", re.I)
REFUSAL = re.compile(r"\bscam\b|\bfraud\b|\bphishing\b|i will not|i won'?t|not giving|call the bank myself"
                     r"|report (you|this)|check (it|this|that) (myself|directly)|i'?d rather (check|call|verify)"
                     r"|i('ll| will) (call|contact|check with) (the|my) (bank|courier|police)"
                     r"|(look( (it|this))? up|check|verify)[^.?!]{0,30}official (site|website|app)|not comfortable"
                     r"|احتيال|نصب|ما بعطيك|ما راح أعطيك|ما راح اعطيك|بتصل بالبنك", re.I)
DISTRESS = re.compile(r"i'?m scared|i am scared|please don'?t|i'?m confused|i am confused|خايف|مب فاهم|ما فهمت شي",
                      re.I)
COMMIT = re.compile(r"my code is|the code is|here is the code|i will read|i'?ll read|let me get my card"
                    r"|i have it in front|الرمز هو|هذا الرمز|بعطيك الرمز", re.I)   # full phrases only
YES = re.compile(r"^(yes|yeah|yep|ok|okay|sure|i do|i have|ready|go ahead|نعم|اي|ايه|هيه|تمام|موجود)\b", re.I)
# Arabic lists below are drafts: a native Emirati speaker must review them before Arabic drills are used for real.
SECRET_THING = (r"(code|otp|password|passcode|pin|card number|card details|cvv|cvc|security (code|number)"
                r"|expiry( date)?|digits|account number)")
ASKS_FOR_SECRET = re.compile(
    r"\b(read|tell|give|say|type|share|enter|send|provide|confirm|write|spell|repeat|reply with|let me have)\b"
    r".{0,40}\b" + SECRET_THING + r"\b"
    r"|what(?:'s| is| are) (the|your) .{0,20}\b" + SECRET_THING + r"\b"
    r"|\blast (four|4) digits\b"
    r"|(اقر[اأ]|عط(ني|نا)|[اأ]عط(ني|نا)|قول|قل لي|طرش|[اأ]رسل|اكتب|دخ[ّ]?ل|شو|كم).{0,40}"
    r"(الرمز|الكود|كلمة السر|الرقم السري|رقم البطاقة|رقم بطاقتك)", re.I)
ROLE_LEAK = re.compile(r"as an ai|language model|system prompt|playbook|\bclaude\b|anthropic|\bkameen\b"
                       r"|role-?play|\bpersona\b|\bdecoy\b|i was playing|(playing|play) (a|the|this|that) (role|part|victim)"
                       r"|i('m| am) (going to stop|not going to continue)|i (won't|will not|can't|cannot) continue"
                       r"|my instructions|scenario card|\bphishing\b|i can'?t help (you )?(with|write|create)"
                       r"|i('m| am) happy to (explain|help)|i('m| am) (not able|unable) to help"
                       r"|ذكاء اصطناعي|نموذج لغوي", re.I)
# The drill agent must never announce the drill: the server does that, with the lesson attached.
SELF_REVEAL = re.compile(
    r"\bkameen\b|\b(a|an|the|this) (training )?(drill|simulation|exercise)\b"
    r"|training (drill|exercise|simulation)|not a real (call|payment|bank|fine|parcel|message)"
    r"|i('m| am) going to stop here|role-?play|(playing|play) (a|the|this|that) (role|part|scammer)"
    r"|i('m| am) (not able|unable) to continue|i (can't|cannot|won't|will not|shouldn't) (continue|keep)"
    r"|i('m| am) not going to (continue|keep|push|press)|^\W*one moment,? please\W*$"
    r"|(do not|don'?t|never) (send|share|give|enter|read)[^.?!]{0,30}(code|card|pin|password|details)"
    r"|simulat\w*|in character|my instructions|scenario card|\bphishing\b"
    r"|i can'?t (do that|discuss|share|help)|(won'?t|can'?t|cannot|will not|never) ask (you )?for"
    r"|safest (step|thing|option)"
    r"|كمين|تمرين|تدريب|محاكاة|مب حقيقي|مش حقيقي|غير حقيقي|(ما|لا|مب) ?[أا]قدر [أا]طلب|ما راح [أا]طلب", re.I)

SECURITY_CODE = re.compile(r"\b((?:cvv2?|cvc2?|security (?:code|number))\D{0,12})\d{3}\b", re.I)
LEFTOVER_DIGITS = re.compile(r"\d+(?:\s*[/.-]\s*\d+)*")

REVEAL_VERDICTS = {"resisted", "attempted_disclosure", "would_comply", "distress"}


def digit_runs(text, minimum):
    """Every run of digits or number words, as a plain digit string, if it has `minimum` digits or more."""
    runs = []
    for match in RUN.finditer(text.translate(EASTERN)):
        units = ONE_UNIT.findall(match.group())
        # "oh" is a zero only inside a number: "6066. Oh sorry" does not end in a zero.
        while units and units[0].lower() == "oh":
            units.pop(0)
        while units and units[-1].lower() == "oh":
            units.pop()
        digits = "".join(WORD_DIGITS.get(u.lower(), u) for u in units)
        if len(digits) >= minimum:
            runs.append((digits, match.span()))
    return runs


def mask_secrets(text, known=()):
    """Masks every run of 4 or more digits, except numbers the agent itself said first, and a
    three-digit card security code. A message that gives one secret often gives the rest
    (an expiry date, a security code), so once anything is masked every other digit goes too."""
    text = text.translate(EASTERN)
    found = False
    for digits, (start, end) in reversed(digit_runs(text, 4)):
        if not any(digits in value for value in known):
            text, found = text[:start] + "[REDACTED]" + text[end:], True
    text, security_codes = SECURITY_CODE.subn(lambda m: m.group(1) + "[REDACTED]", text)
    if found or security_codes:
        text = LEFTOVER_DIGITS.sub("[REDACTED]", text)
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
    if DISTRESS.search(text):
        return masked, "distress"
    if COMMIT.search(text) or (signals and re.search(signals, text, re.I)):
        return masked, "would_comply"
    if conv.awaiting_commit and YES.search(plain(text)):
        return masked, "would_comply"
    if "distress" in conv.risk_flags:                # the director's reading, after anything the person said outright
        return masked, "distress"
    if conv.awaiting_commit:
        return masked, "ask_classifier"
    return masked, "continuing"


def stall_line(conv):
    lines = conv.persona["stall_lines"]
    return lines[conv.turn_count % len(lines)]


def fallback_line(conv):
    if conv.mode == "decoy":
        return stall_line(conv)
    examples = (conv.playbook or {}).get(conv.stage, {}).get("example_lines", [])
    if examples:
        return examples[0]
    return "ألو، بعدك وياي؟" if getattr(conv, "language", "en") == "ar" else "Hello, are you still with me?"


def reveals_drill(conv, sentence):
    """True if the drill agent is about to announce the drill itself."""
    return conv.mode == "drill" and bool(SELF_REVEAL.search(sentence))


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
    if plain(question) in plain(sentence) or "in front of you" in sentence.lower() or "جدامك" in sentence:
        conv.awaiting_commit = True
    conv.agent_digits += [d for d, _ in digit_runs(sentence, 4)]
    return sentence
