"""One place that actually sends an email. Everything that composes a message (phishing-awareness
emails, case notifications) hands it here.

Two backends, picked at send time:
  * SMTP (e.g. Gmail): set SMTP_USER and SMTP_PASSWORD (a Gmail App Password, not the login password).
    This sends from the authenticated account to ANY recipient, which is what a demo without a verified
    domain needs. SMTP_HOST / SMTP_PORT default to Gmail's submission server.
  * Resend's HTTP API: set RESEND_API_KEY (and MAIL_FROM_ADDRESS). Resend's shared sender only reaches
    the account owner until a domain is verified, so SMTP is preferred when both are set.

The display name is the caller's to choose; the from ADDRESS is always the real sending account, so
nothing here can impersonate another mailbox.
"""
import asyncio
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

import httpx


def smtp_configured():
    return bool(os.environ.get("SMTP_USER", "").strip()) and bool(os.environ.get("SMTP_PASSWORD", "").strip())


def resend_configured():
    return bool(os.environ.get("RESEND_API_KEY", "").strip())


def configured():
    return smtp_configured() or resend_configured()


def from_address():
    """The address mail is actually sent from: the SMTP account when SMTP is set, else MAIL_FROM_ADDRESS."""
    if smtp_configured():
        return os.environ.get("SMTP_USER", "").strip()
    return os.environ.get("MAIL_FROM_ADDRESS", "onboarding@resend.dev").strip()


def _send_smtp(from_name, to, subject, html, text, reply_to, headers):
    user = os.environ["SMTP_USER"].strip()
    password = os.environ["SMTP_PASSWORD"].strip().replace(" ", "")   # Gmail shows app passwords in groups of 4
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.environ.get("SMTP_PORT", "587"))
    msg = EmailMessage()
    msg["From"] = formataddr((from_name, user))
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    for key, value in (headers or {}).items():
        msg[key] = value
    msg.set_content(text or "")
    if html:
        msg.add_alternative(html, subtype="html")
    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=20) as server:
        server.starttls(context=context)
        server.login(user, password)
        server.send_message(msg)


async def _send_resend(from_name, to, subject, html, text, reply_to, headers):
    payload = {"from": formataddr((from_name, from_address())), "to": [to],
               "subject": subject, "html": html, "text": text}
    if reply_to:
        payload["reply_to"] = reply_to
    if headers:
        payload["headers"] = headers
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


async def deliver(from_name, to, subject, html, text, reply_to=None, headers=None):
    """Sends one email and returns (ok, error). SMTP first (reaches any recipient), then Resend."""
    if smtp_configured():
        try:
            await asyncio.to_thread(_send_smtp, from_name, to, subject, html, text, reply_to, headers)
            return True, ""
        except Exception as error:
            return False, f"{type(error).__name__}: {error}"[:200]
    if resend_configured():
        return await _send_resend(from_name, to, subject, html, text, reply_to, headers)
    return False, "Email sending is not set up (add SMTP_USER/SMTP_PASSWORD, or a Resend key)."
