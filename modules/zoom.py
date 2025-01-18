import requests
import os

account_id=os.environ["ZOOM_ACCOUNT_ID"]
client_id=os.environ["ZOOM_CLIENT_ID"]
client_secret=os.environ["ZOOM_SECRET_ID"]

auth_token_url = "https://zoom.us/oauth/token"
api_base_url = "https://api.zoom.us/v2"

def create_meeting(topic, start_time, duration):

    access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "topic": topic,
        "duration": duration,
        'start_time': start_time, # date+time
        "type": 2
    }
    resp = requests.post(f"{api_base_url}/users/me/meetings", 
                            headers=headers, 
                            json=payload)
    
    if resp.status_code!=201:
        print("Unable to generate meeting link")
        resp.raise_for_status()
    response_data = resp.json()
    
    content = {
                "meeting_url": response_data["join_url"], 
                "password": response_data["password"],
                "meetingTime": response_data["start_time"],
                "purpose": response_data["topic"],
                "duration": response_data["duration"],
                "message": "Success",
                "status":1
    }
    print(content)
    return response_data["join_url"], response_data["id"]

def get_access_token():
    data = {
    "grant_type": "account_credentials",
    "account_id": account_id,
    "client_secret": client_secret
    }
    response = requests.post(auth_token_url, 
                                auth=(client_id, client_secret), 
                                data=data)
    
    if response.status_code!=200:
        print("Unable to get access token")
        response.raise_for_status()
    else:
        response_data = response.json()
        return response_data["access_token"]

## transcriptions wip, need to test with paid zoom account

def get_recordings():
    headers = {
        "Authorization": f"Bearer {get_access_token}"
    }

    url = f"https://api.zoom.us/v2/users/me/recordings"

    return requests.get(url, headers=headers).json()

def get_download_url():
    recordings = get_recordings()
    if recordings['meetings']: 
        rec_id = recordings['meetings'][0]['id']

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    url = f"https://api.zoom.us/v2/meetings/{rec_id}/recordings"

    r = requests.get(url, headers=headers).json()
    
    url = [i['download_url'] for i in r['recording_files'] if i['recording_type'] == 'audio_only'][0]
    download_link = f'{url}?access_token={self.access_token}&playback_access_token={r["password"]}'
    return download_link

def fetch_zoom_transcript():
    print(get_download_url)

