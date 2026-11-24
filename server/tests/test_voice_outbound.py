"""Outbound awareness calls: Kameen asks ElevenLabs to dial a consented number for a drill.

No call leaves the machine: the ElevenLabs HTTP client is replaced with a recorder.
"""
import pytest

from app import db, voice


class FakeResponse:
    def __init__(self, status=200, data=None):
        self.status_code = status
        self._data = data or {}
        self.content = b"{}"

    def json(self):
        return self._data


class FakeClient:
    def __init__(self, captured, **kwargs):
        self._captured = captured

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json=None, headers=None):
        self._captured.append({"url": url, "json": json, "headers": headers})
        return FakeResponse(200, {"callSid": "CA123", "conversation_id": "el_abc"})


@pytest.fixture
def dialer(monkeypatch):
    """Turns on outbound calling and captures what would be sent to ElevenLabs."""
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-eleven-key")
    monkeypatch.setenv("ELEVENLABS_PHONE_NUMBER_ID", "phnum_test")
    captured = []
    monkeypatch.setattr(voice.httpx, "AsyncClient", lambda **kw: FakeClient(captured, **kw))
    return captured


def call(client, code, **body):
    body = {"to_number": "+971500000001", "scenario_id": "scn_bank_otp_v1", "voice": "english",
            "group_name": "Pilot", "authorised_by": "Officer", "attest": True, **body}
    return client.post("/voice/outbound", json=body, headers=code)


def test_outbound_is_off_without_the_elevenlabs_keys(client, code):
    assert client.get("/voice/outbound", headers=code).json()["ready"] is False
    assert call(client, code).status_code == 503


def test_an_outbound_call_starts_a_drill_and_dials_the_number(client, code, dialer):
    assert client.get("/voice/outbound", headers=code).json()["ready"] is True
    reply = call(client, code)
    assert reply.status_code == 200, reply.text
    conv_id = reply.json()["conversation_id"]
    assert reply.json()["call_sid"] == "CA123"

    sent = dialer[0]["json"]                                         # what ElevenLabs was asked to do
    assert sent["agent_id"] == "agent_en_for_tests" and sent["agent_phone_number_id"] == "phnum_test"
    assert sent["to_number"] == "+971500000001"
    variables = sent["conversation_initiation_client_data"]["dynamic_variables"]
    assert variables["kameen_conversation_id"] == conv_id and variables["opening_line"]
    assert dialer[0]["headers"]["xi-api-key"] == "test-eleven-key"

    detail = client.get(f"/sessions/{conv_id}", headers=code).json()["conversation"]
    assert detail["mode"] == "drill" and detail["channel"] == "voice"


def test_the_voice_window_opens_so_the_call_is_authorised(client, code, dialer):
    conv_id = call(client, code).json()["conversation_id"]
    conv = client.portal.call(db.get_conversation, conv_id)
    assert conv.voice_started_at is not None                        # the model endpoint will now answer for it


def test_outbound_needs_attestation_a_valid_number_and_the_access_code(client, code, dialer):
    assert call(client, code, attest=False).status_code == 400
    assert call(client, code, to_number="0501234567").status_code == 400     # not international format
    assert call(client, code, to_number="+971500000002", scenario_id="nope").status_code == 403
    assert client.post("/voice/outbound", json={"to_number": "+971500000003", "attest": True}).status_code == 401


def test_the_called_number_is_recorded_as_a_voice_consent(client, code, dialer):
    call(client, code, to_number="+971555555555")
    assert client.portal.call(db.find_enrolment, "+971555555555", "voice") is not None


def test_an_arabic_voice_call_uses_the_arabic_agent(client, code, dialer, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_AGENT_AR", "agent_ar_for_tests")
    reply = call(client, code, voice="emirati", scenario_id="scn_traffic_fine_v1", to_number="+971500000009")
    assert reply.status_code == 200, reply.text
    assert dialer[0]["json"]["agent_id"] == "agent_ar_for_tests"
