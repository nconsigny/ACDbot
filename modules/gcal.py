import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import base64
import pytz

SCOPES = ['https://www.googleapis.com/auth/calendar']

def create_event(summary: str, start_dt, duration_minutes: int, calendar_id: str, description=""):
    """
    Creates a Google Calendar event using the Google Calendar API.
    Handles both datetime objects and ISO format strings for start_dt.

    Prerequisites:
    - Environment variable GCAL_SERVICE_ACCOUNT_KEY (JSON string of service account credentials).
      In a production environment, consider using the official 'google-api-python-client' library.

    :param summary: Title/summary of the event
    :param start_dt: Start time of the event (datetime object or ISO format string)
    :param duration_minutes: Event duration in minutes
    :param calendar_id: ID of the Google Calendar
    :param description: Optional text description
    :return: A link (str) to the newly created event
    """

    # Convert start_dt to datetime object if it's a string
    if isinstance(start_dt, str):
        start_dt = datetime.fromisoformat(start_dt.replace('Z', '+00:00'))
    elif not isinstance(start_dt, datetime):
        raise TypeError("start_dt must be a datetime object or ISO format string")
    
    # Ensure timezone awareness
    if not start_dt.tzinfo:
        start_dt = start_dt.replace(tzinfo=pytz.utc)
    
    # Calculate end time using datetime math
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    
    # Format for Google Calendar API
    event_body = {
        'summary': summary,
        'description': description,
        'start': {'dateTime': start_dt.isoformat()},
        'end': {'dateTime': end_dt.isoformat()},
    }

    # Load service account info from environment variable
    service_account_info = json.loads(os.environ['GCAL_SERVICE_ACCOUNT_KEY'])
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES)

    service = build('calendar', 'v3', credentials=credentials)

    event = service.events().insert(calendarId=calendar_id, body=event_body).execute()

    return event.get('htmlLink')
