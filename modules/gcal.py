import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import base64

SCOPES = ['https://www.googleapis.com/auth/calendar']

def create_event(summary: str, start_dt: datetime, duration_minutes: int, calendar_id: str, description=""):
    """
    Creates a Google Calendar event using the Google Calendar API.

    Prerequisites:
    - Environment variable GCAL_SERVICE_ACCOUNT_KEY (JSON string of service account credentials).
      In a production environment, consider using the official 'google-api-python-client' library.

    :param summary: Title/summary of the event
    :param start_dt: Start time of the event (datetime object)
    :param duration_minutes: Event duration in minutes
    :param calendar_id: ID of the Google Calendar
    :param description: Optional text description
    :return: A link (str) to the newly created event
    """

    # Load service account info from environment variable
    service_account_info = json.loads(os.environ['GCAL_SERVICE_ACCOUNT_KEY'])
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES)

    service = build('calendar', 'v3', credentials=credentials)

    end_dt = start_dt + timedelta(minutes=duration_minutes)

    event_body = {
        'summary': summary,
        'description': description,
        'start': {'dateTime': start_dt.isoformat() + 'Z'},
        'end': {'dateTime': end_dt.isoformat() + 'Z'},
    }

    event = service.events().insert(calendarId=calendar_id, body=event_body).execute()

    return event.get('htmlLink')
