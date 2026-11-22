"""Writes every Arabic line Kameen uses into one HTML page for a native reviewer.

Usage (from server/):
    .venv/bin/python scripts/arabic_review.py out.html

The lines are read from the code and the cards, so the page always matches what runs.
Print the page to PDF with any browser.
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import agent, cards, guards, telegram   # noqa: E402

rows = []          # (section, id, where it is used, English meaning, Arabic)
counters = {}


def add(section, letter, where, english, arabic):
    counters[letter] = counters.get(letter, 0) + 1
    rows.append((section, f"{letter}{counters[letter]}", where, english, arabic))


# ---- A. What Kameen itself says in an Arabic drill ----------------------------------------
A = "A. Lines Kameen says at the end of an Arabic drill"
en, ar = agent.DRILL_TEXT["en"], agent.DRILL_TEXT["ar"]
add(A, "A", "First sentence of the reveal, spoken or shown to the trainee", agent.REVEAL_LINE["en"], agent.REVEAL_LINE["ar"])
add(A, "A", "Added when the trainee refused", en["well_done"], ar["well_done"])
add(A, "A", "Added when the trainee said a code or card number", en["not_stored"], ar["not_stored"])
add(A, "A", "Introduces where to report (followed by the scenario's \"Where to report\" line)", en["report"], ar["report"])
add(A, "A", "Said if the trainee keeps talking after the drill ended", en["over"], ar["over"])
add(A, "A", "Said by the drill agent if the model gives no reply", "Hello, are you still with me?", "ألو، بعدك وياي؟")
add(A, "A", "Added when a Telegram drill message was never answered", en["ignored"], ar["ignored"])

# ---- B. The decoy persona -------------------------------------------------------------------
B = "B. Abu Khalid, the decoy persona (a 70-year-old retired Emirati grandfather in Al Ain)"
persona = cards.persona("abu_khalid")
add(B, "B", "Answers the phone", "Hello? Who is this?", persona["opening_line"]["voice"])
add(B, "B", "First words in a text chat", "Who is this?", persona["opening_line"]["text"])
for line, meaning in zip(persona["stall_lines"], [
        "One moment, my son, let me look for my glasses.",
        "I did not hear you well, my son, say that again.",
        "Wait a little, the phone is not clear."]):
    add(B, "B", "Stalling line", meaning, line)
add(B, "B", "Ends the call", "Forgive me, my son, my son Khalid is at the door. I will call you later.", persona["goodbye_line"])

# ---- C. The three drill scenarios -----------------------------------------------------------
SIGNALS = {      # what each Arabic phrase is meant to say; the Arabic list is not a line-by-line copy of the English one
    "بقرا لك الرمز": "I will read you the code",
    "بعطيك الرمز": "I will give you the code",
    "لحظة بشوف الرسايل": "One moment, I will check my messages",
    "وصلني الرمز": "I got the code",
    "لحظة بجيب البطاقة": "One moment, I will get the card",
    "البطاقة عندي": "I have the card",
    "أوكي بدفع": "OK, I will pay",
    "وين أدخل بيانات البطاقة": "Where do I enter the card details?",
}
FIRST = ["scn_bank_otp_v1", "scn_traffic_fine_v1", "scn_courier_parcel_v1"]       # their IDs must not move
for number, scenario_id in enumerate(FIRST + sorted(set(cards.SCENARIOS) - set(FIRST)), 1):
    english, arabic = cards.scenario(scenario_id), cards.scenario(scenario_id, "ar")
    section = f"C{number}. Drill scenario: {english['title']} (Kameen plays the scammer)"
    letter = f"C{number}-"
    for channel, text in arabic["opening_line"].items():
        add(section, letter, f"Opening line ({channel})", english["opening_line"][channel], text)
    add(section, letter, "The one question the agent may ask before the drill stops",
        english["commit_question"], arabic["commit_question"])
    for theirs, ours in zip(english["commit_signals"], arabic["commit_signals"]):
        add(section, letter, "Something a trainee might say that means: I am about to comply",
            SIGNALS.get(ours, theirs), ours)
    for theirs, ours in zip(english["red_flags"], arabic["red_flags"]):
        add(section, letter, "Warning sign shown after the drill", theirs, ours)
    add(section, letter, "Lesson headline", english["lesson"]["headline"], arabic["lesson"]["headline"])
    for theirs, ours in zip(english["lesson"]["three_points"], arabic["lesson"]["three_points"]):
        add(section, letter, "Lesson point", theirs, ours)
    add(section, letter, "Where to report", english["lesson"]["report_to"], arabic["lesson"]["report_to"])

# ---- D. What a trainee might say: Kameen must recognise these -------------------------------
D = ("D. Words a trainee might say. Kameen listens for these. Please correct them and add any "
     "other everyday Emirati ways of saying the same thing.")
add(D, "D", "Trainee wants the drill to stop (only when it is the whole message)", "stop / enough", "وقف  ·  خلاص  ·  خلاص وقف")
add(D, "D", "Trainee refuses or calls it a scam", "fraud / scam / I will not give you / I will call the bank",
    "احتيال  ·  نصب  ·  ما بعطيك  ·  ما راح أعطيك  ·  بتصل بالبنك")
add(D, "D", "Trainee is frightened or lost (the drill stops at once)", "I am scared / I do not understand / I understood nothing",
    "خايف  ·  مب فاهم  ·  ما فهمت شي")
add(D, "D", "Trainee is about to give the code", "the code is… / this is the code / I will give you the code",
    "الرمز هو  ·  هذا الرمز  ·  بعطيك الرمز")
add(D, "D", "Trainee says yes to the question", "yes / ok / I have it", "نعم  ·  اي  ·  ايه  ·  هيه  ·  تمام  ·  موجود")
add(D, "D", "Numbers said as words (so a spoken code is caught and hidden)", "zero to nine, as people say them aloud",
    "صفر  ·  واحد  ·  اثنين / ثنتين  ·  ثلاثة / ثلاث  ·  أربعة / اربع  ·  خمسة / خمس  ·  ستة / ست  ·  "
    "سبعة / سبع  ·  ثمانية / ثمان  ·  تسعة / تسع")

# ---- E. What the agent must never say -------------------------------------------------------
E = ("E. Words Kameen blocks in its own replies. If the drill agent starts a sentence like these, "
     "the sentence is replaced. Please add other ways a caller would ask for a code or card number.")
add(E, "E", "Verbs that ask for something", "read / give me / tell me / send / write / enter / what is / how much",
    "اقرا  ·  عطني / أعطني  ·  قول / قل لي  ·  طرش / أرسل  ·  اكتب  ·  دخّل  ·  شو  ·  كم")
add(E, "E", "The secret being asked for", "the code / the password / the PIN / the card number / your card number",
    "الرمز  ·  الكود  ·  كلمة السر  ·  الرقم السري  ·  رقم البطاقة  ·  رقم بطاقتك")
add(E, "E", "Words that would give the drill away too early", "Kameen / drill / training / simulation / not real",
    "كمين  ·  تمرين  ·  تدريب  ·  محاكاة  ·  مب حقيقي  ·  مش حقيقي  ·  غير حقيقي")
add(E, "E", "Words that would reveal a machine", "artificial intelligence / language model", "ذكاء اصطناعي  ·  نموذج لغوي")
# ---- F. Telegram: what the bot says around a surprise drill ---------------------------------
F = "F. Telegram messages around a surprise drill (consent, waiting, leaving)"
tg_en, tg_ar = telegram.TEXT["en"], telegram.TEXT["ar"]
for key, where in [("consent", "Shown when a person opens the invite link. {group} and {window} are filled in"),
                   ("joined", "After the person replies AGREE"), ("declined", "After any other reply"),
                   ("waiting", "If an enrolled person writes before or after their drill"),
                   ("left", "After /leave"), ("not_enrolled", "After /leave from someone who is not enrolled"),
                   ("invalid", "The invite link is wrong or too old"), ("already", "The person is already enrolled"),
                   ("practice", "Shown the first time a person sends /drill to ask for a practice scam"),
                   ("cancelled", "After any reply other than AGREE to the practice question"),
                   ("running", "If /drill is sent while a drill is already running"),
                   ("none_ready", "If no scenario is approved in the chosen language")]:
    add(F, "F", where, tg_en[key], tg_ar[key])
add(F, "F", "The word that counts as agreement (please list other natural ways to say it)", "AGREE", "أوافق  ·  اوافق  ·  موافق")
add(F, "F", "How the window is written: minutes, hours, days", "10 minutes  ·  3 hours  ·  3 days",
    "  ·  ".join(tg_ar["units"][unit].format(n=n) for unit, n in (("minutes", 10), ("hours", 3), ("days", 3))))

assert all(word in guards.SELF_REVEAL.pattern for word in ("كمين", "تمرين", "محاكاة"))   # the page matches the code

# ---- the page -------------------------------------------------------------------------------
STYLE = """
@page { size: A4 landscape; margin: 12mm; }
body { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; font-size: 10pt; color: #111; margin: 0; }
h1 { font-size: 17pt; margin: 0 0 4pt; }
h2 { font-size: 11.5pt; margin: 14pt 0 5pt; break-after: avoid; }
p { margin: 3pt 0; line-height: 1.4; }
.ar { direction: rtl; text-align: right; font-family: "Geeza Pro", "Al Nile", "Noto Naskh Arabic", "Arial", sans-serif;
      font-size: 13.5pt; line-height: 1.7; }
.intro { border: 1px solid #999; padding: 8pt 10pt; margin: 8pt 0 4pt; }
.intro .ar { font-size: 12pt; }
table { width: 100%; border-collapse: collapse; table-layout: fixed; }
th, td { border: 1px solid #999; padding: 4pt 6pt; vertical-align: top; }
th { background: #eee; font-size: 9pt; text-align: left; }
tr { break-inside: avoid; }
col.id { width: 7%; } col.where { width: 17%; } col.en { width: 22%; } col.arabic { width: 27%; } col.fix { width: 27%; }
td.id { font-weight: 600; white-space: nowrap; }
td.where { color: #444; font-size: 9pt; }
"""


def cell(text, css=""):
    return f'<td class="{css}">{html.escape(text)}</td>'


def page():
    out = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
           "<title>Kameen: Arabic lines for review</title>", f"<style>{STYLE}</style></head><body>",
           "<h1>Kameen (كمين): Arabic lines for review</h1>",
           '<div class="intro">',
           "<p><b>What this is.</b> Kameen is an anti-scam training and decoy system. In a drill it plays a scammer "
           "against a person who agreed to be tested, stops before any secret is given, and then explains the lesson. "
           "Every Arabic line it uses is listed here. They were drafted by a non-native writer and need to sound like "
           "natural Emirati dialect, the way people in the UAE really speak on the phone and in messages.</p>",
           "<p><b>What to do.</b> Read each Arabic line. If it is fine, leave the last column empty. If not, write the "
           "better wording in the last column. In sections D and E, please also add any other common ways of saying "
           "the same thing. Each line has an ID (for example C1-4) so corrections can be sent back as a list of IDs.</p>",
           '<p class="ar">هذي كل الجمل العربية اللي يستخدمها نظام «كمين». نبيها تكون بلهجة إماراتية طبيعية مثل ما يتكلمون '
           'الناس في التلفون والرسايل. إذا الجملة زينة خلّ الخانة الأخيرة فاضية، وإذا تحتاج تعديل اكتب الصيغة الأصح فيها.</p>',
           f"<p>{len(rows)} lines. Scenario cards are approved one language at a time; the Arabic versions go live "
           "with your corrections.</p></div>"]
    current = None
    for section, key, where, english, arabic in rows:
        if section != current:
            if current is not None:
                out.append("</tbody></table>")
            current = section
            out.append(f"<h2>{html.escape(section)}</h2>")
            out.append('<table><colgroup><col class="id"><col class="where"><col class="en"><col class="arabic">'
                       '<col class="fix"></colgroup><thead><tr><th>ID</th><th>Where it is used</th>'
                       "<th>Meaning in English</th><th>Arabic draft</th><th>Correction (leave empty if fine)</th>"
                       "</tr></thead><tbody>")
        out.append("<tr>" + cell(key, "id") + cell(where, "where") + cell(english) + cell(arabic, "ar")
                   + '<td class="ar"></td></tr>')
    out.append("</tbody></table></body></html>")
    return "\n".join(out)


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "arabic_review.html")
    target.write_text(page(), encoding="utf-8")
    print(f"{len(rows)} lines written to {target}")
