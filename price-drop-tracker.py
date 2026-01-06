import requests
import time
from datetime import datetime, timedelta
import os
import glob

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SYMBOLS = ["ISAC.L", "CNDX.L", "CSPX.L", "FLXC.DE", "VWCG.DE", "ETFBW20TR.WA"]
MEMORY_FILE = "/opt/price-drop/last_alerts"
LOG_DIR = "/var/log/price-drop"

def log_to_file(message):
    today = datetime.now().strftime('%Y-%m-%d')
    log_path = os.path.join(LOG_DIR, f"{today}.log")
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)
        
    formatted_msg = f"[{timestamp}] {message}"
    with open(log_path, "a") as f:
        f.write(formatted_msg + "\n")
    print(formatted_msg)

def cleanup_old_logs():
    cutoff = datetime.now() - timedelta(days=7)
    files = glob.glob(os.path.join(LOG_DIR, "*.log"))
    for f in files:
        try:
            file_name = os.path.basename(f).replace(".log", "")
            file_date = datetime.strptime(file_name, '%Y-%m-%d')
            if file_date < cutoff:
                os.remove(f)
                log_to_file(f"System: Deleted old log file {file_name}.log")
        except Exception as e:
            log_to_file(f"System: Error during cleanup of {f}: {e}")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
        log_to_file("Telegram: Notification sent successfully")
    except Exception as e:
        log_to_file(f"Telegram: Error sending message: {e}")

def get_sent_alerts():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return f.read().splitlines()
    return []

def mark_as_sent(symbol_date):
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, "a") as f:
        f.write(f"{symbol_date}\n")

def check_prices():
    today = datetime.now().strftime('%Y-%m-%d')
    sent_alerts = get_sent_alerts()
    cleanup_old_logs()

    for symbol in SYMBOLS:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers).json()
            meta = response['chart']['result'][0]['meta']
            
            current_price = meta['regularMarketPrice']
            previous_close = meta['previousClose']
            change_pct = ((current_price - previous_close) / previous_close) * 100

            log_to_file(f"{symbol}: {current_price} (Change: {change_pct:.2f}%)")

            alert_key = f"{symbol}_{today}"

            if change_pct <= -0.01 and alert_key not in sent_alerts:
                message = (
                    f"📉 Price Alert: {symbol}\n"
                    f"Current Price: {current_price}\n"
                    f"Change: {change_pct:.4f}%"
                )
                send_telegram(message)
                mark_as_sent(alert_key)
                
        except Exception as e:
            log_to_file(f"Error checking {symbol}: {e}")

if __name__ == "__main__":
    log_to_file("Service Status: Started")
    while True:
        check_prices()
        time.sleep(600)