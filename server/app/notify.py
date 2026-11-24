"""Sends the awareness notification for a simulated case, by SMS (Twilio) or email (Resend).

The message is an honest, clearly-labelled note from this project's own brand (ScamShield AI). It never
claims to be the police, a bank or any other body: that would be impersonation, the very thing the
project fights. It is sent only to a number or address the organiser enters and attests consent for.
"""
import os

import httpx

from . import phish


def brand():
    return (os.environ.get("NOTIFY_BRAND", "").strip() or "ScamShield AI")


def sms_sender():
    """A Twilio phone number (reliable), or a registered alphanumeric sender ID if one is set."""
    return (os.environ.get("TWILIO_SMS_SENDER", "").strip()
            or os.environ.get("TWILIO_FROM_NUMBER", "").strip())


def sms_configured():
    return (bool(os.environ.get("TWILIO_ACCOUNT_SID", "").strip())
            and bool(os.environ.get("TWILIO_AUTH_TOKEN", "").strip())
            and bool(sms_sender()))


def email_configured():
    return phish.configured()


def message_text(case_ref):
    """The awareness SMS / email body. Branded as this project, marked as a simulation."""
    b = brand()
    return (f"{b}: you took part in a scam-awareness exercise. In a real scam, the police would open a "
            f"case (demo ref {case_ref}) and you would follow up on TAMM or by calling 8002626. "
            f"This is an awareness simulation from {b}, not a real police case.")


def email_html(case_ref):
    b = brand()
    body = message_text(case_ref)
    return (f'<div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:auto;color:#10272c">'
            f'<p style="font-size:1.1rem;font-weight:600">{b}</p>'
            f'<p>{body}</p>'
            f'<p style="color:#4a6163;font-size:0.85rem">You are receiving this because you agreed to take '
            f'part in a security-awareness exercise. This is not a real case and no action is needed.</p></div>')


async def send_sms(to, body):
    """One SMS through Twilio. Returns (ok, error). Costs money, so it is only ever called on request."""
    sid = os.environ["TWILIO_ACCOUNT_SID"].strip()
    token = os.environ["TWILIO_AUTH_TOKEN"].strip()
    data = {"From": sms_sender(), "To": to, "Body": body}
    try:
        async with httpx.AsyncClient(timeout=20) as http:
            reply = await http.post(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                                    data=data, auth=(sid, token))
    except Exception as error:
        return False, type(error).__name__
    if reply.status_code >= 300:
        try:
            message = reply.json().get("message", "")
        except Exception:
            message = ""
        return False, f"{reply.status_code} {message}".strip()
    return True, ""


async def send_email(to, case_ref):
    """One awareness email through Resend. Returns (ok, error)."""
    payload = {"from": f"{brand()} <{phish.sender_address()}>", "to": [to],
               "subject": f"{brand()} — scam-awareness exercise (simulation)",
               "html": email_html(case_ref), "text": message_text(case_ref)}
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


async def notify(to, case_ref):
    """Sends to an email address or a phone number, chosen by the shape of `to`. Returns (ok, error)."""
    to = (to or "").strip()
    if "@" in to:
        if not email_configured():
            return False, "Email sending is not set up (add a Resend key)."
        return await send_email(to, case_ref)
    if not sms_configured():
        return False, "SMS sending is not set up (add Twilio credentials)."
    return await send_sms(to, message_text(case_ref))
