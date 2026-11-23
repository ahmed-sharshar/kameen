"""Security-awareness phishing emails.

An organiser who is authorised to test a group runs a campaign. Kameen sends each person a
simulated scam email built from an approved scenario card. The only link in it points back to
Kameen; clicking it records the click and immediately shows the person that it was a drill and
what to watch for.

What this never does, by design:
- It never asks for a password, code or card number, and the landing page has no form: nothing
  the person types is collected. The click itself is all that is recorded.
- It never imitates a real bank, company, government body or person. The sender name is a generic
  role ("Refunds Office"), taken from the scenario card, and the link is plainly on Kameen's own
  address, which is the giveaway a careful reader is meant to catch.
- It sends only to the recipients the organiser entered for a campaign they attested to running.
"""
import asyncio
import html
import os
import re
import secrets
import time

import httpx

from . import agent, cards, db, llm

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_RECIPIENTS = 200
_sending = asyncio.Lock()        # one sender at a time: the clock must not overlap a running batch

# Draft Arabic lines: a native Emirati speaker must review them before Arabic campaigns are used for real.
CTA = {"en": "Review the details", "ar": "مراجعة التفاصيل"}
GREETING = {"en": "Dear {name},", "ar": "عزيزي {name}،"}
GREETING_PLAIN = {"en": "Dear customer,", "ar": "عزيزي العميل،"}
FOLLOW = {"en": "Please review this today to avoid any interruption to your account or service.",
          "ar": "الرجاء مراجعة هذا اليوم لتفادي أي توقف في حسابك أو خدمتك."}
BUTTON_HELP = {"en": "If the button does not work, copy and paste this address into your browser:",
               "ar": "إذا ما اشتغل الزر، انسخ هذا العنوان والصقه في المتصفح:"}
SIGN_OFF = {"en": "Kind regards,", "ar": "مع خالص التقدير،"}
SUPPORT_LINE = {"en": "Customer Support", "ar": "خدمة العملاء"}
FOOTER_SENT = {"en": "This message was sent to {email}. Reference {ref}.",
               "ar": "تم إرسال هذه الرسالة إلى {email}. الرقم المرجعي {ref}."}
FOOTER_AUTO = {"en": "This is an automated message. Please do not reply to this email.",
               "ar": "هذه رسالة آلية. الرجاء عدم الرد على هذا البريد."}
# A generic Arabic department name per scenario, mirroring the (generic) English role. No real brand.
SENDER_AR = {
    "scn_bank_otp_v1": "قسم أمان البنك", "scn_traffic_fine_v1": "إدارة المرور",
    "scn_courier_parcel_v1": "خدمة التوصيل", "scn_fake_refund_v1": "مكتب المبالغ المستردة",
    "scn_seized_car_v1": "مبيعات المركبات", "scn_job_visa_fee_v1": "التوظيف الدولي",
    "scn_rental_deposit_v1": "تأجير العقارات", "scn_investment_group_v1": "مجموعة الاستثمار",
}
SAFE_NOTE = {"en": "This was a Kameen security-awareness drill.",
             "ar": "هذا كان تمرين توعية أمنية من كمين."}
REVEAL_SAFE = {"en": "No information was collected. The link you clicked was part of a training exercise.",
               "ar": "ما تم جمع أي معلومات. الرابط اللي ضغطت عليه كان جزء من تمرين تدريبي."}


def configured():
    return bool(os.environ.get("RESEND_API_KEY", "").strip()) and bool(sender_address())


def sender_address():
    return os.environ.get("MAIL_FROM_ADDRESS", "onboarding@resend.dev").strip()


def base_url():
    return (os.environ.get("PUBLIC_URL") or os.environ.get("RENDER_EXTERNAL_URL") or "").rstrip("/")


def new_token():
    return secrets.token_urlsafe(24)


def sender_name(card, language="en"):
    """A generic role, never a real brand: 'a consumer protection refunds office' -> 'Consumer Protection Refunds Office'."""
    if language == "ar":
        return SENDER_AR.get(card["id"], "الإشعارات")
    role = re.sub(r"^(a|an|the)\s+", "", cards.scenario(card["id"])["impersonates"].strip(), flags=re.I)
    return role.title()


def first_name(name):
    return (name or "").strip().split()[0] if (name or "").strip() else ""


def reference(token):
    """A short, official-looking reference derived from the token. Synthetic, like everything else."""
    return "KM-" + "".join(c for c in (token or "") if c.isalnum())[:8].upper()


def _lead(card, language):
    lines = cards.scenario(card["id"], language)["opening_line"]
    for channel in ("email", "whatsapp", "sms", "voice"):
        if lines.get(channel):
            return lines[channel]
    return card.get("hook", "")


def subject(card, language):
    """The SMS opening reads like a subject line ("Traffic Dept: you have an unpaid fine"), so prefer it."""
    lines = cards.scenario(card["id"], language)["opening_line"]
    lead = next((lines[c] for c in ("sms", "email", "whatsapp", "voice") if lines.get(c)), _lead(card, language))
    first = re.split(r"(?<=[.!?؟])\s", lead.strip())[0]
    return first[:120] if first else cards.scenario(card["id"], language).get("title", "Notice")


def _greeting(language, name):
    first = first_name(name)
    if first:
        return GREETING.get(language, GREETING["en"]).format(name=html.escape(first))
    return GREETING_PLAIN.get(language, GREETING_PLAIN["en"])


def email_html(card, language, link, name="", email="", token=""):
    """A clean, brand-free transactional-looking email. The one clickable link is the tracking link."""
    rtl = language == "ar"
    side = "right" if rtl else "left"
    sender = html.escape(sender_name(card, language))
    initials = html.escape("".join(w[0] for w in sender.split()[:2]).upper() or "K")
    cta = html.escape(CTA.get(language, CTA["en"]))
    greeting = _greeting(language, name)
    paras = "".join(f"<p style='margin:0 0 16px'>{html.escape(p)}</p>" for p in
                    (greeting, _lead(card, language), FOLLOW.get(language, FOLLOW["en"])))
    footer = html.escape(FOOTER_SENT.get(language, FOOTER_SENT["en"]).format(
        email=email or "you", ref=reference(token)))
    auto = html.escape(FOOTER_AUTO.get(language, FOOTER_AUTO["en"]))
    help_line = html.escape(BUTTON_HELP.get(language, BUTTON_HELP["en"]))
    sign = html.escape(SIGN_OFF.get(language, SIGN_OFF["en"]))
    support = html.escape(SUPPORT_LINE.get(language, SUPPORT_LINE["en"]))
    return f"""<!doctype html><html lang="{language}" dir="{'rtl' if rtl else 'ltr'}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{sender}</title></head>
<body style="margin:0;background:#eef1f4;padding:24px 0;font:16px/1.65 -apple-system,'Segoe UI',Roboto,Tahoma,Arial,sans-serif;color:#1d2a35;text-align:{side}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto">
<tr><td style="background:#0b5c66;padding:18px 24px;border-radius:12px 12px 0 0">
  <table role="presentation" cellpadding="0" cellspacing="0"><tr>
    <td style="width:40px"><div style="width:40px;height:40px;background:#ffffff22;border:1px solid #ffffff55;border-radius:50%;color:#fff;font-weight:600;text-align:center;line-height:40px">{initials}</div></td>
    <td style="padding:0 12px;color:#fff;font-size:17px;font-weight:600">{sender}</td>
  </tr></table>
</td></tr>
<tr><td style="background:#fff;padding:26px 24px;border:1px solid #e2e8ee;border-top:none">
  {paras}
  <table role="presentation" cellpadding="0" cellspacing="0" style="margin:22px 0"><tr><td style="border-radius:8px;background:#0b5c66">
    <a href="{html.escape(link)}" style="display:inline-block;padding:13px 30px;color:#fff;text-decoration:none;font-weight:600;font-size:16px">{cta}</a>
  </td></tr></table>
  <p style="margin:0 0 4px;font-size:13px;color:#6b7a88">{help_line}</p>
  <p style="margin:0 0 20px;font-size:13px;color:#6b7a88;word-break:break-all"><a href="{html.escape(link)}" style="color:#0b5c66;text-decoration:none">{html.escape(link)}</a></p>
  <p style="margin:0">{sign}</p>
  <p style="margin:2px 0 0;color:#5a6b7a">{sender} &middot; {support}</p>
</td></tr>
<tr><td style="padding:16px 24px;background:#f6f8fa;border:1px solid #e2e8ee;border-top:none;border-radius:0 0 12px 12px;font-size:12px;color:#8795a2;line-height:1.6">
  <p style="margin:0 0 4px">{auto}</p>
  <p style="margin:0">{footer}</p>
</td></tr>
</table></body></html>"""


def email_text(card, language, link, name="", email="", token=""):
    return "\n\n".join([
        _greeting(language, name), _lead(card, language), FOLLOW.get(language, FOLLOW["en"]),
        CTA.get(language, CTA["en"]) + ": " + link,
        SIGN_OFF.get(language, SIGN_OFF["en"]) + " " + sender_name(card, language),
        FOOTER_SENT.get(language, FOOTER_SENT["en"]).format(email=email or "you", ref=reference(token))])


async def send_one(target):
    """Sends one email through Resend. Returns (ok, error)."""
    card = cards.scenario(target.scenario_id, target.language)
    link = base_url() + "/t/" + target.token
    payload = {
        "from": f"{sender_name(card, target.language)} <{sender_address()}>", "to": [target.email],
        "reply_to": sender_address(), "subject": subject(card, target.language),
        "html": email_html(card, target.language, link, target.name, target.email, target.token),
        "text": email_text(card, target.language, link, target.name, target.email, target.token),
        # Standard header for authorised bulk mail; helps deliverability and is good practice.
        "headers": {"List-Unsubscribe": f"<mailto:{sender_address()}?subject=unsubscribe>"},
    }
    try:
        async with httpx.AsyncClient(timeout=20) as http:
            reply = await http.post("https://api.resend.com/emails", json=payload,
                                    headers={"Authorization": "Bearer " + os.environ["RESEND_API_KEY"].strip()})
    except Exception as error:
        return False, type(error).__name__
    if reply.status_code >= 300:
        try:
            message = reply.json().get("message", "")
        except Exception:
            message = ""
        return False, f"{reply.status_code} {message}".strip()
    return True, ""


async def send_queued():
    """Sends every queued email. Run from the one-minute clock and right after a campaign is created."""
    if not configured():
        return 0
    sent = 0
    async with _sending:                              # a second caller waits, then finds nothing queued
        for target in await db.queued_targets():
            ok, error = await send_one(target)
            await db.mark_target(target.id, "sent" if ok else "failed", error)
            if ok:
                sent += 1
            else:
                llm.log("phish email failed:", error)
            await asyncio.sleep(0.3)                  # Resend's free tier allows a couple per second
    return sent


async def start_campaign(group_name, scenario_id, language, authorised_by, recipients):
    """Validates and queues a campaign, then kicks off sending. Returns (code, queued, skipped)."""
    language = language if language in ("en", "ar") else "en"
    approved = [card_id for card_id in cards.SCENARIOS
                if cards.scenario(card_id, language)["language"] == language
                and cards.scenario(card_id, language).get("approved_by")]
    if scenario_id and scenario_id not in approved:
        raise ValueError("That scenario is not approved in that language.")
    if not approved:
        raise ValueError("No scenario is approved in that language yet.")

    seen, queued = set(), []
    for person in recipients:
        name = str(person.get("name", "")).strip()
        email = str(person.get("email", "")).strip().lower()
        if not EMAIL.match(email) or email in seen:
            continue
        seen.add(email)
        scn = scenario_id or secrets.choice(approved)
        queued.append(((name or email.split("@")[0])[:80], email, new_token(), scn))
        if len(queued) >= MAX_RECIPIENTS:
            break
    if not queued:
        raise ValueError("No valid email addresses were given.")

    code = secrets.token_urlsafe(8).replace("-", "a").replace("_", "b")
    await db.add_campaign(code, group_name, scenario_id, language, authorised_by, queued)
    agent.run_later(send_queued())
    return code, len(queued), len(recipients) - len(queued)


def reveal_page(scenario_id, language, name):
    """The page the link lands on: no form, nothing to type. It reveals the drill and teaches."""
    card = cards.scenario(scenario_id, language)
    lesson = card["lesson"]
    rtl = language == "ar"
    words = agent.DRILL_TEXT.get(language, agent.DRILL_TEXT["en"])
    hello = (f"مرحباً {html.escape(name)}، " if rtl else f"Hello {html.escape(name)}, ") if name else ""
    points = "".join(f"<li style='margin:0 0 10px'>{html.escape(p)}</li>" for p in lesson["three_points"])
    report = html.escape(words["report"] + lesson["report_to"].rstrip(".") + ".")
    heading = html.escape(SAFE_NOTE.get(language, SAFE_NOTE["en"]))
    reveal = html.escape(hello + agent.REVEAL_LINE.get(language, agent.REVEAL_LINE["en"]))
    safe = html.escape(REVEAL_SAFE.get(language, REVEAL_SAFE["en"]))
    return f"""<!doctype html><html lang="{language}" dir="{'rtl' if rtl else 'ltr'}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Kameen</title>
<style>
body{{margin:0;background:#eef3f1;font:17px/1.6 -apple-system,'Segoe UI',Tahoma,Arial,sans-serif;color:#13272c}}
.card{{max-width:620px;margin:40px auto;background:#fff;border:1px solid #d7e0de;border-radius:16px;padding:30px 28px}}
.flag{{display:inline-block;background:#e2eff0;color:#073f47;border-radius:999px;padding:4px 14px;font-weight:600;font-size:14px}}
h1{{font-size:24px;margin:16px 0 6px}} h2{{font-size:17px;margin:26px 0 10px}}
ul{{padding-{'right' if rtl else 'left'}:22px;margin:0}} .report{{margin-top:22px;color:#4a6163}}
</style></head><body><div class="card">
<span class="flag">{heading}</span>
<h1>{reveal}</h1>
<p>{safe}</p>
<h2>{html.escape(lesson['headline'].rstrip('.'))}.</h2>
<ul>{points}</ul>
<p class="report">{report}</p>
</div></body></html>"""
