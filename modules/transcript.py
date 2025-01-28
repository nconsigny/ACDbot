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
    # Load the mapping to find the corresponding Discourse topic ID
    mapping = load_meeting_topic_mapping()
    discourse_topic_id = mapping.get(meeting_id, {}).get("discourse_topic_id")
    if not discourse_topic_id:
        raise ValueError(f"No Discourse topic mapping found for meeting ID {meeting_id}")

    # Check if transcript exists before fetching from Zoom
    if discourse.check_if_transcript_posted(topic_id=discourse_topic_id, meeting_id=meeting_id):
        print(f"Transcript for meeting {meeting_id} already exists in topic {discourse_topic_id}")
        return

    # Get transcript text
    transcript_text = zoom.get_meeting_transcript(meeting_id)
    if not transcript_text:
        raise ValueError(f"No transcript found for meeting {meeting_id}")

    # Upload transcript as file
    file_name = f"transcript-{meeting_id}.txt"
    transcript_url = discourse.upload_file(transcript_text, file_name)
    
    # Get and format summary
    summary = zoom.get_meeting_summary(meeting_id)
    summary_text = ""
    if summary and 'summary' in summary:
        summary_text = f"**AI Summary:**\n{summary['summary']}\n\n"
    
    # Create post with summary and transcript link
    post_content = f"{summary_text}**Meeting Transcript:** [Download {file_name}]({transcript_url})"
    discourse.create_post(topic_id=discourse_topic_id, body=post_content)
    
    print(f"Transcript for meeting {meeting_id} posted to Discourse topic {discourse_topic_id}")

    # Update mapping if needed (e.g., if we obtained the topic ID here)
    # mapping[meeting_id] = discourse_topic_id
    # save_meeting_topic_mapping(mapping)
