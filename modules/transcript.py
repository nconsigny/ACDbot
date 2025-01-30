import os
import json
from modules import zoom, discourse
import requests

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
    Posts the Zoom meeting recording link and summary to Discourse.
    """
    # Load the mapping to find the corresponding Discourse topic ID
    mapping = load_meeting_topic_mapping()
    entry = mapping.get(str(meeting_id))  # Ensure string key lookup
    
    # Handle both old and new format
    if isinstance(entry, dict):
        discourse_topic_id = entry.get("discourse_topic_id")
    else:  # Legacy string format
        discourse_topic_id = entry
        
    if not discourse_topic_id:
        raise ValueError(f"No Discourse topic mapping found for meeting ID {meeting_id}")

    # Check existing posts
    if discourse.check_if_transcript_posted(discourse_topic_id, meeting_id):
        print(f"Transcript already posted for meeting {meeting_id}")
        return discourse_topic_id

    # Get recording details to obtain UUID
    recording_data = zoom.get_meeting_recording(meeting_id)
    meeting_uuid = recording_data.get('uuid', '')
    
    # Format UUID by removing slashes (required by API)
    formatted_uuid = meeting_uuid.replace('/', '').strip() if meeting_uuid else meeting_id
    
    # Get summary using formatted UUID
    summary_data = zoom.get_meeting_summary(formatted_uuid)
    
    # Extract summary text
    summary = summary_data.get('summary_details', {}).get('summary_content',
                recording_data.get('summary', 'No summary available yet'))
    
    # Extract proper share URL and passcode (new format)
    share_url = recording_data.get('share_url', '')
    passcode = recording_data.get('password', '')
    
    # Get transcript download URL from recording files
    transcript_url = next(
        (f['download_url'] for f in recording_data.get('recording_files', [])
         if f['file_type'] == 'TRANSCRIPT'),
        None
    )

    # Build post content with actual summary text
    post_content = f"""**Meeting Summary:**
{summary}

**Recording Access:**
- [Join Recording Session]({share_url}) (Passcode: `{passcode}`)"""

    # Add transcript link if available
    if transcript_url:
        post_content += f"\n- [Download Transcript]({transcript_url})"

    discourse.create_post(
        topic_id=discourse_topic_id,
        body=post_content
    )
    
    print(f"Posted recording links for meeting {meeting_id} to topic {discourse_topic_id}")
    return discourse_topic_id
