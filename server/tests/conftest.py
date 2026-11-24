import os
import sys
import tempfile
from pathlib import Path

# Configure the app before it is imported: a throwaway database, the scripted model, known codes.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["KAMEEN_FAKE_MODEL"] = "1"
os.environ["ACCESS_CODE"] = "test-code"
os.environ["ADMIN_CODE"] = "test-admin"
os.environ["LLM_SHARED_SECRET"] = "test-secret"
os.environ["DRILL_COOLDOWN_HOURS"] = "0"
os.environ["FRONTEND_ORIGIN"] = "http://localhost:5500"
os.environ["ELEVENLABS_AGENT_EN_IN"] = "agent_for_tests"      # Rajesh's voice
os.environ["ELEVENLABS_AGENT_EN"] = "agent_en_for_tests"      # Sara's voice and English drills
os.environ["ELEVENLABS_AGENT_AR"] = "unset"                   # the Arabic agent stays unconfigured
os.environ["ELEVENLABS_API_KEY"] = "unset"
os.environ["RESEND_API_KEY"] = "test-resend-key"            # phish.configured() is True; no real send in tests
os.environ["MAIL_FROM_ADDRESS"] = "drills@kameen.test"
os.environ["PUBLIC_URL"] = "https://kameen.test"
os.environ.pop("VOICE_REQUIRE_SECRET", None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from app import cards, notify
from app.main import app

CODE = {"X-Access-Code": "test-code"}


@pytest.fixture(autouse=True)
def no_real_case_email(monkeypatch):
    """No test sends a real case email to Resend. test_cases overrides this to capture them."""
    async def stub(case):
        return True, ""
    monkeypatch.setattr(notify, "send_case_email", stub)


@pytest.fixture(scope="session")
def client():
    for card in cards.SCENARIOS.values():          # tests stand in for the human reviewer
        card["approved_by"] = "test"
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def code():
    return CODE
