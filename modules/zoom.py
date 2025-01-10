import os
import json
import requests

def create_zoom_meeting(title: str, start_time: str) -> str:
    """
    Creates a Zoom meeting and returns the join URL.
    Expects environment variables:
      - ZOOM_JWT
      - ZOOM_USER_ID
    """
    zoom_jwt = os.environ["ZOOM_JWT"]            # fails if not found
    zoom_user_id = os.environ["ZOOM_USER_ID"]    # fails if not found

    payload = {
        "topic": title,
        "type": 2,  # scheduled meeting
        "start_time": start_time,
        "duration": 60,
        "settings": {
            "host_video": True,
            "participant_video": True,
            "auto_recording": "cloud"
        }
    }

    url = f"https://api.zoom.us/v2/users/{zoom_user_id}/meetings"
    headers = {
        "Authorization": f"Bearer {zoom_jwt}",
        "Content-Type": "application/json",
    }

    resp = requests.post(url, headers=headers, data=json.dumps(payload))
    resp.raise_for_status()

    data = resp.json()
    return data["join_url"]

def fetch_zoom_transcript(meeting_id: str) -> str:
    """
    Fetches the transcript text for a Zoom meeting's cloud recording.

    1) Calls Zoom's /meetings/{meeting_id}/recordings endpoint
    2) Finds a recording file with file_type="TRANSCRIPT"
    3) Downloads the transcript text
    4) Returns that text

    Expects environment variable:
      - ZOOM_JWT (or valid Oauth token)
    """
    zoom_jwt = os.environ["ZOOM_JWT"]  # Make sure your JWT or OAuth token can access recordings

    # Step 1: Get the recording files
    recordings_url = f"https://api.zoom.us/v2/meetings/{meeting_id}/recordings"
    headers = {
        "Authorization": f"Bearer {zoom_jwt}",
        "Content-Type": "application/json",
    }

    resp = requests.get(recordings_url, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    # Step 2: Locate a transcript file in "recording_files"
    transcript_url = None
    for fileinfo in data.get("recording_files", []):
        if fileinfo.get("file_type") == "TRANSCRIPT":
            transcript_url = fileinfo.get("download_url")
            break

    if not transcript_url:
        raise ValueError(f"No transcript file found for meeting {meeting_id}")

    # Step 3: Download the transcript from the transcript_url
    # Depending on Zoom settings, we may need to pass the same Bearer token or add ?access_token=...
    # For many accounts, you can do the Authorization header again:
    transcript_resp = requests.get(transcript_url, headers=headers)
    transcript_resp.raise_for_status()

    # The transcript text is typically returned as plain text (VTT or similar)
    transcript_text = transcript_resp.text

    return transcript_text
