import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def create_event(summary: str, start_dt: datetime, duration_minutes: int, calendar_id: str, description=""):
    """
    Creates a Google Calendar event using the Google Calendar API.

    Prerequisites:
    - Environment variable GCAL_ACCESS_TOKEN (OAuth token or service account token).
      In a production environment, consider using the official 'google-api-python-client' library.

    :param summary: Title/summary of the event
    :param start_dt: Start time of the event (datetime object)
    :param duration_minutes: Event duration in minutes
    :param calendar_id: ID of the Google Calendar
    :param description: Optional text description
    :return: A link (str) to the newly created event
    """
    access_token = os.environ["GCAL_ACCESS_TOKEN"]
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    event_json = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_dt.isoformat() + "Z"},
        "end": {"dateTime": end_dt.isoformat() + "Z"},
    }

    url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    resp = requests.post(url, headers=headers, data=json.dumps(event_json))
    resp.raise_for_status()

    return resp.json().get("htmlLink")
