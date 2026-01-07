import requests
import time
from datetime import datetime, timedelta
import os
import glob

from file.logs import log_to_file, cleanup_old_logs
from file.check_alert_send import get_sent_alerts, mark_as_sent
from telegram.send import send_telegram

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# SYMBOLS = ["ISAC.L"]
SYMBOLS = ["ISAC.L", "CNDX.L", "CSPX.L", "FLXC.DE", "VWCG.DE", "ETFBW20TR.WA"]

def is_market_open():
    current_hour = datetime.now().hour
    return 9 <= current_hour < 20

def check_prices():
    if not is_market_open():
        return

    today = datetime.now().strftime('%Y-%m-%d')
    sent_alerts = get_sent_alerts()
    cleanup_old_logs()

    for symbol in SYMBOLS:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers).json()
            meta = response['chart']['result'][0]['meta']
            print(meta)
            
            current_price = meta['regularMarketPrice']
            previous_close = meta['previousClose']
            change_pct = ((current_price - previous_close) / previous_close) * 100

            log_to_file(f"{symbol}: {current_price} (Change: {change_pct:.2f}%)")

            alert_key = f"{symbol}_{today}"

            if change_pct <= -1 and alert_key not in sent_alerts:
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
    log_to_file("================================ Service Status: Started ================================")
    while True:
        check_prices()
        time.sleep(600)