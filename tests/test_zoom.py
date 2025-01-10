# tests/test_zoom.py
import os
import pytest
from modules.zoom import create_zoom_meeting

@pytest.mark.vcr  # If you use pytest-vcr for mocking requests
def test_create_zoom_meeting(monkeypatch):
    monkeypatch.setenv("ZOOM_JWT", "fake_jwt")
    monkeypatch.setenv("ZOOM_USER_ID", "fake_user")

    # Potentially mock requests.post here
    # e.g., monkeypatch.setattr("requests.post", mock_post_function)

    # If your function just does "requests.post(...)",
    # you'd verify if it raises or returns the correct data structure
    # For demonstration, assume it returns a dummy link:
    with pytest.raises(Exception):
        create_zoom_meeting("Test Meeting", "2025-01-01T00:00:00Z")
