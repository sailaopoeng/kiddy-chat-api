import os
import sys
from pathlib import Path

import pytest

# Configure the app before it is imported: in-memory sessions, a dummy key.
for name in (
    "UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN",
    "UPSTASH2_KV_REST_API_URL", "UPSTASH2_KV_REST_API_TOKEN",
    "KV_REST_API_URL", "KV_REST_API_TOKEN",
    "PARENT_PIN", "PARENT_SIGNING_SECRET",
):
    os.environ.pop(name, None)
os.environ["OPENAI_API_KEY"] = "sk-test-key"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content=None, delta=None):
        self.message = FakeMessage(content)
        self.delta = FakeMessage(delta)


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content=content)]


class FakeChunk:
    def __init__(self, delta):
        self.choices = [FakeChoice(delta=delta)]


class FakeStream:
    def __init__(self, deltas):
        self._deltas = list(deltas)
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._deltas:
            raise StopAsyncIteration
        return FakeChunk(self._deltas.pop(0))

    async def close(self):
        self.closed = True


class FakeCompletions:
    def __init__(self):
        self.reply = "Hello there!"
        self.stream_deltas = ["Hello ", "there!"]
        self.calls = []
        self.error = None

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        if kwargs.get("stream"):
            return FakeStream(self.stream_deltas)
        return FakeResponse(self.reply)


class FakeOpenAI:
    def __init__(self):
        self.chat = type("Chat", (), {})()
        self.chat.completions = FakeCompletions()


@pytest.fixture
def fake_openai(monkeypatch):
    fake = FakeOpenAI()
    monkeypatch.setattr(main, "client", fake)
    return fake.chat.completions


@pytest.fixture
def api(fake_openai):
    main.sessions.clear()
    main.memory_counters.clear()
    with TestClient(main.app) as test_client:
        yield test_client
    main.sessions.clear()
    main.memory_counters.clear()


@pytest.fixture
def pin(monkeypatch):
    """Turn on the grown-up PIN for one test."""
    value = "246810"
    monkeypatch.setattr(main, "parent_pin", value)
    monkeypatch.setattr(main, "parent_signing_key", b"test-signing-key")
    return value


def start_session(api, username="Mia"):
    response = api.post("/initiate-session", json={"username": username})
    assert response.status_code == 200
    return response.json()["session_id"]


def auth(session_id):
    return {"Authorization": f"Bearer {session_id}"}
