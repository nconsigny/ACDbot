import os
import json
from modules import zoom, discourse

MAPPING_FILE = "meeting_topic_mapping.json"

def load_meeting_topic_mapping():
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r") as f:
            return json.load(f)
    return {}

def post_zoom_transcript_to_discourse(meeting_id: str):
    """
    Posts the Zoom meeting transcript as a reply to the corresponding Discourse topic.
    """
    # Load the mapping to find the corresponding Discourse topic ID
    mapping = load_meeting_topic_mapping()
    discourse_topic_id = mapping.get(meeting_id)
    if not discourse_topic_id:
        raise ValueError(f"No Discourse topic mapping found for meeting ID {meeting_id}")

    # Fetch the transcript from Zoom
    transcript_text = zoom.get_meeting_transcript(meeting_id)
    if not transcript_text:
        raise ValueError(f"No transcript found for meeting {meeting_id}")

    # Check if the transcript has already been posted
    transcript_already_posted = discourse.check_if_transcript_posted(
        topic_id=discourse_topic_id,
        meeting_id=meeting_id
    )
    if transcript_already_posted:
        print(f"Transcript for meeting {meeting_id} has already been posted.")
        return

    # Post the transcript as a reply to the topic
    post_content = f"**Transcript for Meeting ID {meeting_id}:**\n\n{transcript_text}"
    discourse.create_post(topic_id=discourse_topic_id, body=post_content)
    print(f"Transcript for meeting {meeting_id} posted to Discourse topic {discourse_topic_id}.")
