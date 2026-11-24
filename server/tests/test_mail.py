"""The email backend: SMTP (any recipient) is preferred, Resend is the fallback. No mail is sent for real."""
import asyncio

from app import mail


class FakeSMTP:
    """Stands in for smtplib.SMTP so no connection is made; records the message that would be sent."""
    last = None

    def __init__(self, host, port, timeout=None):
        self.host, self.port, self.logged_in, self.started_tls, self.sent = host, port, None, False, None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.started_tls = True

    def login(self, user, password):
        self.logged_in = (user, password)

    def send_message(self, msg):
        self.sent = msg
        FakeSMTP.last = self


def test_configured_prefers_smtp_then_resend(monkeypatch):
    for var in ("SMTP_USER", "SMTP_PASSWORD", "RESEND_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    assert not mail.configured()
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    assert mail.configured() and not mail.smtp_configured()      # Resend only
    monkeypatch.setenv("SMTP_USER", "me@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "abcd efgh ijkl mnop")
    assert mail.smtp_configured() and mail.from_address() == "me@gmail.com"


def test_smtp_sends_to_any_recipient(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "me@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "abcd efgh ijkl mnop")   # spaces as Gmail shows them
    monkeypatch.setattr(mail.smtplib, "SMTP", FakeSMTP)

    ok, err = asyncio.run(mail.deliver("ScamShield AI", "anyone@gmail.com", "Case AMAN-1",
                                       "<b>hello</b>", "hello"))
    assert ok and err == ""
    msg = FakeSMTP.last.sent
    assert msg["To"] == "anyone@gmail.com"                       # not the account owner — any address works
    assert msg["From"] == "ScamShield AI <me@gmail.com>"         # real account, honest display name
    assert msg["Subject"] == "Case AMAN-1"
    assert FakeSMTP.last.started_tls and FakeSMTP.last.logged_in == ("me@gmail.com", "abcdefghijklmnop")
    assert "hello" in msg.get_body(("html",)).get_content()


def test_no_backend_is_a_clean_error_not_a_crash(monkeypatch):
    for var in ("SMTP_USER", "SMTP_PASSWORD", "RESEND_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    ok, err = asyncio.run(mail.deliver("ScamShield AI", "x@example.com", "s", "<b>h</b>", "h"))
    assert not ok and "not set up" in err
