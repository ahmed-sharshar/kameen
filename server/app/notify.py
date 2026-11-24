"""Emails the details of a simulated case to the awareness-team address when a person is caught out.

Honest, clearly-labelled note from this project's own brand (ScamShield AI). It never claims to be the
police, a bank or any other body. Email only (SMS was removed); sending reuses the existing Resend setup.
"""
import html as _html
import os

from . import mail


def brand():
    return os.environ.get("NOTIFY_BRAND", "").strip() or "ScamShield AI"


def alert_email():
    """Where a 'fooled' case from the default number is emailed automatically."""
    return os.environ.get("CASE_ALERT_EMAIL", "").strip() or "ahmed.sharshar5@gmail.com"


def auto_email_number():
    """A fooled case is emailed automatically only for this number; others wait for a manual send."""
    return os.environ.get("AUTO_EMAIL_NUMBER", "").strip() or "+971585919310"


def email_configured():
    return mail.configured()


FIELDS = [("Case reference", "case_ref"), ("Person", "person"), ("Channel", "channel"),
          ("Scam type", "scam_type"), ("Outcome", "outcome"), ("Group", "group_name"),
          ("Identity (UAE Pass, simulated)", "emirates_id"), ("Contact", "contact")]


def _contact(case):
    return case.get("email") or case.get("phone") or "-"


def case_html(case):
    b = _html.escape(brand())
    rows = "".join(
        f'<tr><td style="padding:4px 14px 4px 0;color:#4a6163">{_html.escape(label)}</td>'
        f'<td style="padding:4px 0;font-weight:600">{_html.escape(str(case.get(key) or (_contact(case) if key == "contact" else "-")))}</td></tr>'
        for label, key in FIELDS)
    return (f'<div style="font-family:Arial,Helvetica,sans-serif;max-width:600px;margin:auto;color:#10272c">'
            f'<p style="font-size:1.15rem;font-weight:600">{b} — scam-awareness case</p>'
            f'<p>A person was caught out in a scam-awareness exercise. The case details are below. '
            f'This is a simulation, not a real police case.</p>'
            f'<table style="border-collapse:collapse;margin-top:8px">{rows}</table>'
            f'<p style="color:#4a6163;font-size:0.85rem;margin-top:16px">Sent automatically by {b}. '
            f'Not connected to TAMM, UAE Pass or the Aman service.</p></div>')


def case_text(case):
    lines = [f"{brand()} — scam-awareness case (simulation, not a real police case)", ""]
    for label, key in FIELDS:
        lines.append(f"{label}: {case.get(key) or (_contact(case) if key == 'contact' else '-')}")
    return "\n".join(lines)


async def send_email(to, subject, html, text):
    """One email, branded as this project (SMTP to any recipient, or Resend). Returns (ok, error)."""
    return await mail.deliver(from_name=brand(), to=to, subject=subject, html=html, text=text)


async def send_case_email(case, to):
    """Emails the case details to `to`. Returns (ok, error)."""
    if not email_configured():
        return False, "Email sending is not set up (add SMTP_USER/SMTP_PASSWORD, or a Resend key)."
    subject = f"{brand()} — case {case.get('case_ref')} ({case.get('person')})"
    return await send_email(to, subject, case_html(case), case_text(case))
