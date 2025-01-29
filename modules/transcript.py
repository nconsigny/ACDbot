import os
import json
from modules import zoom, discourse

MAPPING_FILE = "meeting_topic_mapping.json"

def load_meeting_topic_mapping():
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r") as f:
            return json.load(f)
    return {}

def save_meeting_topic_mapping(mapping):
    with open(MAPPING_FILE, "w") as f:
        json.dump(mapping, f)

def post_zoom_transcript_to_discourse(meeting_id: str):
    """
    Posts the Zoom meeting transcript as a file attachment and summary as text.
    """
    # Load mapping and verify topic ID
    mapping = load_meeting_topic_mapping()
    entry = mapping.get(meeting_id)
    discourse_topic_id = entry.get("discourse_topic_id") if isinstance(entry, dict) else entry
    if not discourse_topic_id:
        raise ValueError(f"No Discourse topic mapping found for meeting ID {meeting_id}")

    # Check existing posts
    if discourse.check_if_transcript_posted(discourse_topic_id, meeting_id):
        print(f"Transcript already posted for meeting {meeting_id}")
        return discourse_topic_id

    # Get transcript and summary
    transcript_text = zoom.get_meeting_transcript(meeting_id)
    summary_data = zoom.get_meeting_summary(meeting_id)
    summary = summary_data.get('summary', 'No summary available yet')

    # Upload transcript file
    file_name = f"transcript-{meeting_id}.txt"
    transcript_url = discourse.upload_file(transcript_text, file_name)

    # Create post with summary and transcript link
    post_content = f"""**Meeting Summary:**
{summary}

**Full Transcript:**
[Download {file_name}]({transcript_url})"""

    discourse.create_post(
        topic_id=discourse_topic_id,
        body=post_content
    )
    
    print(f"Posted transcript for meeting {meeting_id} to topic {discourse_topic_id}")
    return discourse_topic_id
