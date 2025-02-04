import os
import time
import tempfile
import requests
import argparse
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from modules.zoom import (
    get_meeting_recording,
    get_access_token,
    get_meeting_summary 
)
from google.auth.transport.requests import Request
import json
import subprocess

# Reuse existing zoom module functions
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS_FILE = "client_secrets.json"

# Add these functions at the top of the file
MAPPING_FILE = "meeting_topic_mapping.json"

def get_authenticated_service():
    # Get credentials from environment variables
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )
    
    # Refresh if needed
    if not creds.valid:
        creds.refresh(Request())
        
    return build("youtube", "v3", credentials=creds)

def video_exists(youtube, meeting_id):
    """Check if video for this meeting ID already exists in mapping"""
    mapping = load_meeting_topic_mapping()
    return mapping.get(meeting_id, {}).get("youtube_video_id") is not None

def download_zoom_recording(meeting_id):
    """Download Zoom recording MP4 file to temp location"""
    recording_info = get_meeting_recording(meeting_id)
    
    if not recording_info or 'recording_files' not in recording_info:
        return None

    for file in recording_info['recording_files']:
        if file.get('file_type') == 'MP4' and file.get('download_url'):
            download_url = file['download_url']
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            
            headers = {
                "Authorization": f"Bearer {get_access_token()}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(download_url, headers=headers, stream=True)
            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk:
                        temp_file.write(chunk)
                temp_file.close()
                return temp_file.name
    return None

def upload_recording(meeting_id):
    youtube = get_authenticated_service()
    
    # Replace zoom.get_meeting() with proper data source
    mapping = load_meeting_topic_mapping()
    meeting_data = mapping.get(meeting_id, {})
    
    # Get meeting title from mapping or default
    video_title = meeting_data.get("topic", f"Meeting {meeting_id}")
    
    # If you need additional meeting info, use existing functions:
    recording_info = get_meeting_recording(meeting_id)
    # Or: meeting_summary = get_meeting_summary(meeting_id)
    
    if video_exists(youtube, meeting_id):
        print(f"YouTube video already exists for meeting {meeting_id}")
        return

    video_path = download_zoom_recording(meeting_id)
    if not video_path:
        print(f"No MP4 recording available for meeting {meeting_id}")
        return

    try:
        title = f"Ethereum Protocol Call - {video_title}"
        description = f"Recording of Ethereum protocol call meeting {meeting_id}"

        request_body = {
            'snippet': {
                'title': title,
                'description': description,
                'categoryId': '28'
            },
            'status': {
                'privacyStatus': 'public',
            }
        }

        media = googleapiclient.http.MediaFileUpload(video_path, chunksize=-1, resumable=True)
        response = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media
        ).execute()

        # Update mapping with YouTube video ID
        mapping[meeting_id] = mapping.get(meeting_id, {})
        mapping[meeting_id]["youtube_video_id"] = response['id']
        save_meeting_topic_mapping(mapping)
        commit_mapping_file()
        
        print(f"Uploaded YouTube video: https://youtu.be/{response['id']}")

    except HttpError as e:
        print(f"YouTube API error: {e}")
    finally:
        os.unlink(video_path)  # Clean up temp file

def main():
    parser = argparse.ArgumentParser(description="Upload Zoom recording to YouTube")
    parser.add_argument("--meeting_id", required=True, help="Zoom meeting ID to process")
    args = parser.parse_args()
    
    upload_recording(args.meeting_id)

def load_meeting_topic_mapping():
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r") as f:
            return json.load(f)
    return {}

def save_meeting_topic_mapping(mapping):
    with open(MAPPING_FILE, "w") as f:
        json.dump(mapping, f, indent=2)

def commit_mapping_file():
    """Commit and push changes to the mapping file"""
    try:
        # Configure git user (required in CI)
        subprocess.run(
            ["git", "config", "--global", "user.email", "actions@github.com"],
            check=True
        )
        subprocess.run(
            ["git", "config", "--global", "user.name", "GitHub Actions"],
            check=True
        )
        
        # Commit and push
        subprocess.run(["git", "add", MAPPING_FILE], check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Update YouTube video mapping"],
            check=True
        )
        subprocess.run(["git", "push"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to commit mapping file: {e}")

if __name__ == "__main__":
    main() 