import requests
from datetime import datetime

from src.config import (
    SYMBOLS, SYMBOL_NAMES, ALERT_THRESHOLD_FIRST, ALERT_THRESHOLD_STEP,
    MARKET_OPEN_HOUR, MARKET_CLOSE_HOUR
)
from src.logs import log_to_file, cleanup_old_logs
from src.alerts import get_alert_thresholds, save_alert_threshold, cleanup_alert_file
from src.telegram import send_telegram

last_check_time = None
last_check_status = None


def get_next_threshold(current_change_pct):
    threshold = ALERT_THRESHOLD_FIRST
    while threshold >= current_change_pct:
        threshold += ALERT_THRESHOLD_STEP
    return threshold - ALERT_THRESHOLD_STEP


def get_last_check_status():
    return last_check_status


def check_prices():
    global last_check_time, last_check_status
    
    try:
        current_time = datetime.now()
        hour = current_time.hour
        if hour < MARKET_OPEN_HOUR or hour >= MARKET_CLOSE_HOUR:
            log_to_file(f"Market closed ({current_time.strftime('%H:%M:%S')}). Skipping check.")
            return

        log_to_file(f"Check prices triggered at {current_time.strftime('%H:%M:%S')}")

        cleanup_alert_file()
        alert_thresholds = get_alert_thresholds()
        cleanup_old_logs()

        results = []

        for symbol in SYMBOLS:
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d"
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers, timeout=10).json()
                meta = response['chart']['result'][0]['meta']
                
                current_price = meta['regularMarketPrice']
                previous_close = meta['previousClose']
                change_pct = ((current_price - previous_close) / previous_close) * 100

                symbol_name = SYMBOL_NAMES.get(symbol, symbol)
                log_to_file(f"{symbol} ({symbol_name}): {current_price} (Change: {change_pct:.2f}%)")
                
                result = {
                    "symbol": symbol,
                    "name": symbol_name,
                    "price": current_price,
                    "change_pct": change_pct,
                    "status": "checked"
                }

                if change_pct <= ALERT_THRESHOLD_FIRST:
                    last_sent_threshold = alert_thresholds.get(symbol, 0.0)
                    current_threshold = get_next_threshold(change_pct)
                    if current_threshold < last_sent_threshold:
                        message = (
                            f"📉 Price Alert: {symbol_name}\n"
                            f"Current Price: {current_price}\n"
                            f"Change: {change_pct:.4f}%"
                        )
                        send_telegram(message)
                        save_alert_threshold(symbol, current_threshold)
                        result["alert_sent"] = True
                        result["threshold"] = current_threshold
                        log_to_file(f"Alert sent for {symbol_name}: threshold {current_threshold}")
                    else:
                        result["alert_sent"] = False
                else:
                    result["alert_sent"] = False
                    
                results.append(result)
                
            except Exception as e:
                log_to_file(f"Error checking {symbol}: {e}")
                results.append({
                    "symbol": symbol,
                    "status": "error",
                    "error": str(e)
                })

        last_check_time = datetime.now().isoformat()
        last_check_status = {
            "timestamp": last_check_time,
            "results": results,
            "success": True
        }
        
    except Exception as e:
        log_to_file(f"Critical error in check_prices: {e}")
        last_check_status = {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "success": False
        }
