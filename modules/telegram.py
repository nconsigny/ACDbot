import os
import requests

def send_message(text: str):
    """
    Sends a message to a Telegram channel or group.
    Expects environment variables:
      - TELEGRAM_BOT_TOKEN
      - TELEGRAM_CHAT_ID
    """
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }

    resp = requests.post(url, data=data)
    resp.raise_for_status()

    return resp.json()
