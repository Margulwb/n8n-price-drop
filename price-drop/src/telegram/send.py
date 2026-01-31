import requests
import os
from src.file.logs import log_to_file

def send_telegram(message):
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    TOKEN = os.getenv("TELEGRAM_TOKEN")

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
        log_to_file("Telegram: Notification sent successfully")
    except Exception as e:
        log_to_file(f"Telegram: Error sending message: {e}")