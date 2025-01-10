# tests/test_discourse.py
import pytest
import os
from modules import discourse

def test_create_topic(monkeypatch, requests_mock):
    """
    Tests that create_topic successfully sends the correct POST request
    and returns the JSON response from the Discourse API.
    """

    # 1. Set environment variables (fake credentials/base URL)
    monkeypatch.setenv("DISCOURSE_API_KEY", "fake_api_key")
    monkeypatch.setenv("DISCOURSE_API_USERNAME", "fake_user")
    monkeypatch.setenv("DISCOURSE_BASE_URL", "http://fake-discourse.local")

    # 2. Prepare a mock response for the Discourse POST request
    mock_response = {
        "topic_id": 123,
        "status": "ok",
        "title": "Fake Title"
    }

    # 3. Mock the POST endpoint
    requests_mock.post("http://fake-discourse.local/posts.json",
                       json=mock_response,
                       status_code=200)

    # 4. Call the function under test
    result = discourse.create_topic(title="Test Title", body="Test Body", category_id=63)

    # 5. Verify the correct POST data was sent
    history = requests_mock.request_history
    assert len(history) == 1
    
    posted_data = history[0].json()
    assert posted_data["title"] == "Test Title"
    assert posted_data["raw"] == "Test Body"
    assert posted_data["category"] == 63

    # 6. Check the returned JSON matches our mock response
    assert result["topic_id"] == 123
    assert result["status"] == "ok"
    assert result["title"] == "Fake Title"
