import os
import argparse
from datetime import datetime, timedelta
import pytz  # Install via pip if not already installed
from modules import zoom, transcript

def is_meeting_eligible(meeting_end_time):
    """
    Check if the meeting ended more than 4 hours ago.
    """
    now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
    time_difference = now_utc - meeting_end_time
    return time_difference >= timedelta(hours=4)

def main():
    parser = argparse.ArgumentParser(description="Poll Zoom for recordings and post transcripts.")
    parser.add_argument("--force_meeting_id", help="Force processing of a specific Zoom meeting ID")
    args = parser.parse_args()

    if args.force_meeting_id:
        meeting_id = args.force_meeting_id
        print(f"Force processing meeting {meeting_id}")
        try:
            transcript.post_zoom_transcript_to_discourse(meeting_id)
        except Exception as e:
            print(f"Error processing meeting {meeting_id}: {e}")
        return

    # Fetch recordings from Zoom
    recordings = zoom.get_recordings_list()
    for meeting in recordings:
        meeting_id = meeting.get("id")
        uuid = meeting.get("uuid")
        topic = meeting.get("topic")
        end_time_str = meeting.get("end_time")
        if not meeting_id or not end_time_str:
            continue  # Skip if essential data is missing

        # Parse end time
        meeting_end_time = datetime.strptime(end_time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
        if is_meeting_eligible(meeting_end_time):
            print(f"Processing meeting {meeting_id}: {topic}")
            try:
                transcript.post_zoom_transcript_to_discourse(str(meeting_id))
            except Exception as e:
                print(f"Error processing meeting {meeting_id}: {e}")
        else:
            print(f"Meeting {meeting_id} is not yet eligible for processing.")

if __name__ == "__main__":
    main()
