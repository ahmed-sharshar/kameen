"""One place that actually sends an email. Everything that composes a message (phishing-awareness
emails, case notifications) hands it here.

Backends, tried in this order (HTTP first, because our host Render blocks outbound SMTP ports on the
free plan, so a plain SMTP connection times out there):
  * SendGrid HTTP API (SENDGRID_API_KEY): sends over HTTPS, so it works on Render. With SendGrid's
    single-sender verification you verify ONE from address (e.g. a Gmail) and can then send to ANY
    recipient with no domain to buy. This is the recommended setup for this project.
  * Resend HTTP API (RESEND_API_KEY, MAIL_FROM_ADDRESS): also HTTPS, but its shared sender only reaches
    the account owner until a domain is verified.
  * SMTP (SMTP_USER + SMTP_PASSWORD, e.g. a Gmail App Password): sends from the authenticated account to
    any recipient. Works locally, but NOT on Render's free plan (SMTP ports are blocked there).

The from ADDRESS is MAIL_FROM_ADDRESS when set, else the SMTP account; it must be an address the chosen
provider is allowed to send from (a verified sender). The display name is the caller's to choose, so
nothing here can impersonate another mailbox.
"""
import asyncio
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

import httpx


def sendgrid_configured():
    return bool(os.environ.get("SENDGRID_API_KEY", "").strip())


def smtp_configured():
    return bool(os.environ.get("SMTP_USER", "").strip()) and bool(os.environ.get("SMTP_PASSWORD", "").strip())


def resend_configured():
    return bool(os.environ.get("RESEND_API_KEY", "").strip())


def configured():
    return sendgrid_configured() or resend_configured() or smtp_configured()


def from_address():
    """The address mail is sent from: MAIL_FROM_ADDRESS when customised, else the SMTP account, else the
    Resend shared sender. For SendGrid or Resend this must be a sender that provider has verified."""
    explicit = os.environ.get("MAIL_FROM_ADDRESS", "").strip()
    if explicit and explicit != "onboarding@resend.dev":
        return explicit
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    if smtp_user:
        return smtp_user
    return explicit or "onboarding@resend.dev"


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


async def _send_sendgrid(from_name, to, subject, html, text, reply_to, headers):
    content = []
    if text:
        content.append({"type": "text/plain", "value": text})
    content.append({"type": "text/html", "value": html or text or ""})      # SendGrid needs plain before html
    payload = {
        "personalizations": [{"to": [{"email": to}]}],
        "from": {"email": from_address(), "name": from_name},
        "subject": subject, "content": content,
    }
    if reply_to:
        payload["reply_to"] = {"email": reply_to}
    if headers:
        payload["headers"] = {key: str(value) for key, value in headers.items()}
    try:
        async with httpx.AsyncClient(timeout=20) as http:
            reply = await http.post("https://api.sendgrid.com/v3/mail/send", json=payload,
                                    headers={"Authorization": "Bearer " + os.environ["SENDGRID_API_KEY"].strip()})
    except Exception as error:
        return False, type(error).__name__
    if reply.status_code >= 300:
        try:
            errors = reply.json().get("errors") or []
            message = "; ".join(e.get("message", "") for e in errors) or reply.text[:150]
        except Exception:
            message = reply.text[:150]
        return False, f"{reply.status_code} {message}".strip()
    return True, ""


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
    """Sends one email and returns (ok, error). HTTP providers first (they work on Render, which blocks
    outbound SMTP): SendGrid, then Resend, then SMTP as a local/other-host fallback."""
    if sendgrid_configured():
        return await _send_sendgrid(from_name, to, subject, html, text, reply_to, headers)
    if resend_configured():
        return await _send_resend(from_name, to, subject, html, text, reply_to, headers)
    if smtp_configured():
        try:
            await asyncio.to_thread(_send_smtp, from_name, to, subject, html, text, reply_to, headers)
            return True, ""
        except Exception as error:
            return False, f"{type(error).__name__}: {error}"[:200]
    return False, "Email sending is not set up (add a SendGrid or Resend key, or SMTP_USER/SMTP_PASSWORD)."
