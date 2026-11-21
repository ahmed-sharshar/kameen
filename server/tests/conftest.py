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
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from app import cards
from app.main import app

CODE = {"X-Access-Code": "test-code"}


@pytest.fixture(scope="session")
def client():
    for card in cards.SCENARIOS.values():          # tests stand in for the human reviewer
        card["approved_by"] = "test"
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def code():
    return CODE
