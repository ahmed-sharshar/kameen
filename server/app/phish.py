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
CTA = {"en": "Open", "ar": "فتح"}
GREETING = {"en": "Dear customer,", "ar": "عزيزي العميل،"}
FOLLOW = {"en": "Please act on this today to avoid any interruption to your account or service.",
          "ar": "الرجاء التصرف اليوم لتفادي أي توقف في حسابك أو خدمتك."}
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


def sender_name(card):
    """A generic role, never a real brand: 'a consumer protection refunds office' -> 'Consumer Protection Refunds Office'."""
    role = re.sub(r"^(a|an|the)\s+", "", cards.scenario(card["id"])["impersonates"].strip(), flags=re.I)
    return role.title()


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


def email_html(card, language, link):
    """A plain, brand-free HTML email. The one link is the tracking link."""
    rtl = language == "ar"
    cta = html.escape(CTA.get(language, CTA["en"]))
    body = "".join(f"<p style='margin:0 0 16px'>{html.escape(part)}</p>" for part in
                   (GREETING.get(language, GREETING["en"]), _lead(card, language), FOLLOW.get(language, FOLLOW["en"])))
    return f"""<!doctype html><html lang="{language}" dir="{'rtl' if rtl else 'ltr'}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;background:#f2f4f7;font:16px/1.6 -apple-system,'Segoe UI',Tahoma,Arial,sans-serif;color:#1b2733">
<div style="max-width:560px;margin:0 auto;padding:24px">
  <div style="background:#0b5c66;color:#fff;padding:14px 20px;border-radius:10px 10px 0 0;font-weight:600">
    {html.escape(sender_name(card))}
  </div>
  <div style="background:#fff;padding:22px 20px;border:1px solid #e2e8ee;border-top:none;border-radius:0 0 10px 10px">
    {body}
    <p style="margin:24px 0 8px;text-align:{'right' if rtl else 'left'}">
      <a href="{html.escape(link)}" style="display:inline-block;background:#0b5c66;color:#fff;text-decoration:none;
        padding:12px 26px;border-radius:8px;font-weight:600">{cta}</a>
    </p>
  </div>
</div></body></html>"""


def email_text(card, language, link):
    return "\n\n".join([GREETING.get(language, GREETING["en"]), _lead(card, language),
                        FOLLOW.get(language, FOLLOW["en"]), CTA.get(language, CTA["en"]) + ": " + link])


async def send_one(target):
    """Sends one email through Resend. Returns (ok, error)."""
    card = cards.scenario(target.scenario_id, target.language)
    link = base_url() + "/t/" + target.token
    payload = {"from": f"{sender_name(card)} <{sender_address()}>", "to": [target.email],
               "subject": subject(card, target.language),
               "html": email_html(card, target.language, link), "text": email_text(card, target.language, link)}
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
