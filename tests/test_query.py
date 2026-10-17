import json

import main
from conftest import auth, start_session


def read_events(response):
    """Parse a text/event-stream body into [(event, data), ...]."""
    events = []
    for block in response.text.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((fields["event"], json.loads(fields["data"])))
    return events


def test_query_returns_reply_and_keeps_history(api, fake_openai):
    session_id = start_session(api)
    response = api.post("/query", json={"message": "Hi!"}, headers=auth(session_id))
    assert response.status_code == 200
    assert response.json()["response"] == "Hello there!"

    history = api.get(f"/session/{session_id}/history", headers=auth(session_id)).json()["messages"]
    assert [m["role"] for m in history] == ["system", "user", "assistant"]
    assert fake_openai.calls[0]["model"] == main.OPENAI_MODEL


def test_filtered_message_is_not_sent_to_openai(api, fake_openai):
    session_id = start_session(api)
    response = api.post("/query", json={"message": "you are stupid"}, headers=auth(session_id))
    assert response.json()["response"] in main.KIDS_FRIENDLY_RESPONSES
    assert fake_openai.calls == []


def test_unsafe_ai_reply_is_replaced(api, fake_openai):
    fake_openai.reply = "That movie has a scary monster."
    session_id = start_session(api)
    response = api.post("/query", json={"message": "Tell me a story"}, headers=auth(session_id))
    assert response.json()["response"] == main.SAFE_REPLACEMENT_MESSAGE


def test_openai_error_gives_friendly_message(api, fake_openai):
    fake_openai.error = RuntimeError("boom")
    session_id = start_session(api)
    response = api.post("/query", json={"message": "Hi"}, headers=auth(session_id))
    assert response.status_code == 200
    assert response.json()["response"] == main.AI_ERROR_MESSAGE


def test_stream_sends_only_complete_sentences(api, fake_openai):
    fake_openai.stream_deltas = ["Hello the", "re! I am a ro", "bot. And I like ", "pi, which is 3.14"]
    session_id = start_session(api)
    response = api.post("/query/stream", json={"message": "Hi"}, headers=auth(session_id))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = read_events(response)
    deltas = [data["text"] for event, data in events if event == "delta"]
    assert deltas == ["Hello there!", " I am a robot."]
    assert events[-1] == ("done", {
        "response": "Hello there! I am a robot. And I like pi, which is 3.14",
        "session_id": session_id,
        "username": "Mia",
    })
    assert fake_openai.calls[0]["stream"] is True

    history = api.get(f"/session/{session_id}/history", headers=auth(session_id)).json()["messages"]
    assert history[-1]["content"] == "Hello there! I am a robot. And I like pi, which is 3.14"


def test_stream_never_sends_a_blocked_word(api, fake_openai):
    fake_openai.stream_deltas = ["Fun fact! ", "Some caves are ", "very scary. ", "Bye."]
    session_id = start_session(api)
    events = read_events(api.post("/query/stream", json={"message": "Hi"}, headers=auth(session_id)))

    sent_text = "".join(data["text"] for event, data in events if event == "delta")
    assert sent_text == "Fun fact!"
    assert events[-1][1]["response"] == main.SAFE_REPLACEMENT_MESSAGE


def test_stream_does_not_flag_half_words(api, fake_openai):
    # "di" + "et" must not be checked as the blocked word "die".
    fake_openai.stream_deltas = ["Eat a healthy di", "et every day."]
    session_id = start_session(api)
    events = read_events(api.post("/query/stream", json={"message": "Hi"}, headers=auth(session_id)))
    assert events[-1][1]["response"] == "Eat a healthy diet every day."


def test_stream_with_filtered_input_sends_only_done(api, fake_openai):
    session_id = start_session(api)
    events = read_events(api.post("/query/stream", json={"message": "shut up"}, headers=auth(session_id)))
    assert [event for event, _ in events] == ["done"]
    assert events[0][1]["response"] in main.KIDS_FRIENDLY_RESPONSES
    assert fake_openai.calls == []


def test_stream_error_ends_with_friendly_message(api, fake_openai):
    fake_openai.error = RuntimeError("boom")
    session_id = start_session(api)
    events = read_events(api.post("/query/stream", json={"message": "Hi"}, headers=auth(session_id)))
    assert events == [("done", {"response": main.AI_ERROR_MESSAGE, "session_id": session_id, "username": "Mia"})]


def test_query_needs_a_valid_session(api):
    assert api.post("/query", json={"message": "Hi"}, headers=auth("nope")).status_code == 401
    assert api.post("/query/stream", json={"message": "Hi"}, headers=auth("nope")).status_code == 401


def test_rate_limit(api, monkeypatch):
    monkeypatch.setattr(main, "QUERY_RATE_LIMIT_PER_MINUTE", 2)
    session_id = start_session(api)
    for _ in range(2):
        assert api.post("/query", json={"message": "Hi"}, headers=auth(session_id)).status_code == 200
    assert api.post("/query", json={"message": "Hi"}, headers=auth(session_id)).status_code == 429
    assert api.post("/query/stream", json={"message": "Hi"}, headers=auth(session_id)).status_code == 429

    # Other sessions are not affected.
    other = start_session(api, "Leo")
    assert api.post("/query", json={"message": "Hi"}, headers=auth(other)).status_code == 200


def test_input_size_limits(api):
    assert api.post("/initiate-session", json={"username": "x" * 51}).status_code == 422
    session_id = start_session(api)
    too_long = "a" * (main.MAX_MESSAGE_LENGTH + 1)
    assert api.post("/query", json={"message": too_long}, headers=auth(session_id)).status_code == 422


def test_safe_stream_boundary():
    assert main.safe_stream_boundary("No end yet") == 0
    assert main.safe_stream_boundary("One. Two") == len("One.")
    assert main.safe_stream_boundary("Pi is 3.14") == 0
    assert main.safe_stream_boundary("Line one\nLine two") == len("Line one\n")
