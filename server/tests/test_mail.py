"""The email backend. HTTP providers (SendGrid, Resend) are preferred because Render blocks outbound
SMTP; SMTP is the local fallback. No mail is sent for real: smtplib and httpx are stubbed."""
import asyncio

from app import mail

ENV = ("SENDGRID_API_KEY", "RESEND_API_KEY", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM_ADDRESS")


def clear(monkeypatch):
    for var in ENV:
        monkeypatch.delenv(var, raising=False)


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


class FakeResponse:
    def __init__(self, status_code, body=None, text=""):
        self.status_code, self._body, self.text = status_code, body or {}, text

    def json(self):
        return self._body


def fake_http(capture, response):
    """A stand-in httpx.AsyncClient that records the one request and returns `response`."""
    class FakeClient:
        def __init__(self, timeout=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None, headers=None):
            capture.update(url=url, json=json, auth=(headers or {}).get("Authorization"))
            return response
    return FakeClient


def test_configured_and_from_address(monkeypatch):
    clear(monkeypatch)
    assert not mail.configured()
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    assert mail.configured() and not mail.sendgrid_configured() and not mail.smtp_configured()
    monkeypatch.setenv("SMTP_USER", "me@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "pw")
    assert mail.smtp_configured() and mail.from_address() == "me@gmail.com"      # no explicit from -> SMTP account
    monkeypatch.setenv("MAIL_FROM_ADDRESS", "alerts@scamshield.example")
    assert mail.from_address() == "alerts@scamshield.example"                    # an explicit from wins
    monkeypatch.setenv("SENDGRID_API_KEY", "SG.test")
    assert mail.sendgrid_configured()


def test_sendgrid_is_preferred_and_reaches_any_recipient(monkeypatch):
    clear(monkeypatch)
    monkeypatch.setenv("SENDGRID_API_KEY", "SG.test")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")                 # present too, but SendGrid wins (HTTP, Render-safe)
    monkeypatch.setenv("MAIL_FROM_ADDRESS", "scamshiel.ai@gmail.com")
    seen = {}
    monkeypatch.setattr(mail.httpx, "AsyncClient", fake_http(seen, FakeResponse(202)))

    ok, err = asyncio.run(mail.deliver("ScamShield AI", "farida@gmail.com", "Case AMAN-1", "<b>hi</b>", "hi"))
    assert ok and err == ""
    assert seen["url"].endswith("/v3/mail/send")                   # SendGrid endpoint, not Resend
    assert seen["json"]["personalizations"][0]["to"][0]["email"] == "farida@gmail.com"   # any recipient
    assert seen["json"]["from"] == {"email": "scamshiel.ai@gmail.com", "name": "ScamShield AI"}
    assert seen["auth"] == "Bearer SG.test"


def test_sendgrid_surfaces_a_clear_error(monkeypatch):
    clear(monkeypatch)
    monkeypatch.setenv("SENDGRID_API_KEY", "SG.test")
    body = {"errors": [{"message": "The from address does not match a verified Sender Identity."}]}
    monkeypatch.setattr(mail.httpx, "AsyncClient", fake_http({}, FakeResponse(403, body)))
    ok, err = asyncio.run(mail.deliver("ScamShield AI", "x@gmail.com", "s", "<b>h</b>", "h"))
    assert not ok and "verified Sender Identity" in err


def test_smtp_is_the_fallback_and_sends_to_any_recipient(monkeypatch):
    clear(monkeypatch)
    monkeypatch.setenv("SMTP_USER", "me@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "abcd efgh ijkl mnop")      # spaces as Gmail shows them
    monkeypatch.setattr(mail.smtplib, "SMTP", FakeSMTP)

    ok, err = asyncio.run(mail.deliver("ScamShield AI", "anyone@gmail.com", "Case", "<b>hello</b>", "hello"))
    assert ok and err == ""
    msg = FakeSMTP.last.sent
    assert msg["To"] == "anyone@gmail.com"
    assert msg["From"] == "ScamShield AI <me@gmail.com>"
    assert FakeSMTP.last.started_tls and FakeSMTP.last.logged_in == ("me@gmail.com", "abcdefghijklmnop")
    assert "hello" in msg.get_body(("html",)).get_content()


def test_no_backend_is_a_clean_error_not_a_crash(monkeypatch):
    clear(monkeypatch)
    ok, err = asyncio.run(mail.deliver("ScamShield AI", "x@example.com", "s", "<b>h</b>", "h"))
    assert not ok and "not set up" in err
