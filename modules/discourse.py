import os
import json
import requests

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def create_topic(title: str, body: str, category_id=63):
    """
    Creates a new Discourse topic.
    Expects environment variables:
      - DISCOURSE_API_KEY
      - DISCOURSE_API_USERNAME
      - DISCOURSE_BASE_URL (defaults to https://ethereum-magicians.org)
    """
    api_key = os.environ["DISCOURSE_API_KEY"]
    api_user = os.environ["DISCOURSE_API_USERNAME"]
    base_url = os.environ.get("DISCOURSE_BASE_URL", "https://ethereum-magicians.org")

    payload = {
        "title": title,
        "raw": body,
        "category": category_id,
        "archetype": "regular"
    }

    resp = requests.post(
        f"{base_url}/posts.json",
        headers={
            "Api-Key": api_key,
            "Api-Username": api_user,
            "Content-Type": "application/json",
        },
        data=json.dumps(payload),
    )
    if not resp.ok:
        print(resp.text)  # Log the response content for debugging
        resp.raise_for_status()

    return resp.json()
