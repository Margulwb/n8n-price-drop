import requests
from src.config import TELEGRAM_CHAT_ID, TELEGRAM_TOKEN
from src.logs import log_to_file


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})
        log_to_file("Telegram: Notification sent successfully")
    except Exception as e:
        log_to_file(f"Telegram: Error sending message: {e}")