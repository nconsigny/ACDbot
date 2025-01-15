import os
import json
import requests
import logging
from datetime import datetime, timedelta
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_zoom_access_token():
    try:
        client_id = os.environ["ZOOM_CLIENT_ID"]
        client_secret = os.environ["ZOOM_CLIENT_SECRET"]
    except KeyError as e:
        logger.error(f"Missing environment variable: {e}")
        raise

    token_url = "https://zoom.us/oauth/token"

    client = BackendApplicationClient(client_id=client_id)
    oauth = OAuth2Session(client=client)

    try:
        token = oauth.fetch_token(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            include_client_id=True
        )
        logger.info("Successfully obtained Zoom access token.")
        return token["access_token"]
    except Exception as e:
        logger.error(f"Error obtaining Zoom access token: {e}")
        raise

def create_zoom_meeting(title: str, start_time: str, duration_minutes: int = 60) -> str:
    """
    Creates a Zoom meeting and returns the join URL.
    Expects environment variables:
      - ZOOM_CLIENT_ID
      - ZOOM_CLIENT_SECRET
      - ZOOM_ACCOUNT_ID

    :param title: Title of the Zoom meeting
    :param start_time: Start time in ISO 8601 format (UTC)
    :param duration_minutes: Duration of meeting in minutes (default 60)
    :return: URL to join the Zoom meeting
    """
    access_token = get_zoom_access_token()
    zoom_account_id = os.environ["ZOOM_ACCOUNT_ID"]  # Replace ZOOM_USER_ID with ZOOM_ACCOUNT_ID

    payload = {
        "topic": title,
        "type": 2,  # Scheduled meeting
        "start_time": start_time,
        "duration": duration_minutes,
        "settings": {
            "host_video": True,
            "participant_video": True,
            "auto_recording": "cloud"
        }
    }

    url = f"https://api.zoom.us/v2/users/{zoom_account_id}/meetings"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    resp = requests.post(url, headers=headers, data=json.dumps(payload))
    resp.raise_for_status()

    data = resp.json()
    return data["join_url"]

def fetch_zoom_transcript(meeting_id: str) -> str:
    """
    Fetches the transcript text for a Zoom meeting's cloud recording.

    Steps:
    1) Retrieve recording files via Zoom's API.
    2) Find the transcript file.
    3) Download the transcript.
    4) Return the transcript text.

    Expects environment variables:
      - ZOOM_CLIENT_ID
      - ZOOM_CLIENT_SECRET
    """
    access_token = get_zoom_access_token()

    # Step 1: Get the recording files
    recordings_url = f"https://api.zoom.us/v2/meetings/{meeting_id}/recordings"
    headers = {
        "Authorization": f"Bearer {access_token}",
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

    # Step 3: Download the transcript
    # Append the access_token as a query parameter
    transcript_resp = requests.get(f"{transcript_url}?access_token={access_token}")
    transcript_resp.raise_for_status()

    transcript_text = transcript_resp.text
    return transcript_text
