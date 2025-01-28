import os
import time
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS_FILE = "client_secrets.json"  # Downloaded from Google Cloud Console

def get_authenticated_service():
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, SCOPES)
    
    credentials = flow.run_local_server(port=8080, prompt='consent')
    return googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)

def video_exists(youtube, title):
    """Check if a video with the same title already exists."""
    search_response = youtube.search().list(
        q=title,
        part='id',
        type='video',
        maxResults=1
    ).execute()
    
    return len(search_response.get('items', [])) > 0

def upload_video(video_file_path, title, description):
    youtube = get_authenticated_service()
    
    # Check if video already exists
    if video_exists(youtube, title):
        print(f"Video with title '{title}' already exists. Skipping upload.")
        return None

    request_body = {
        'snippet': {
            'title': title,
            'description': description,
            'categoryId': '28'  # Category ID for 'Science & Technology'
        },
        'status': {
            'privacyStatus': 'public',  # Options: 'public', 'private', 'unlisted'
        }
    }

    media_file = googleapiclient.http.MediaFileUpload(video_file_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media_file
    )

    response = None
    while response is None:
        try:
            print("Uploading video...")
            status, response = request.next_chunk()
            if response is not None:
                print("Video uploaded successfully!")
                return response['id']  # Return the YouTube video ID
        except googleapiclient.errors.HttpError as e:
            print(f"An HTTP error {e.resp.status} occurred: {e.content}")
            break
    return None 