import requests
from datetime import datetime
import os
from flask import Flask, jsonify, render_template
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

from src.file.logs import log_to_file, cleanup_old_logs
from src.file.check_alert_send import get_sent_alerts, mark_as_sent
from src.telegram.send import send_telegram

app = Flask(__name__, template_folder='templates')

CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SYMBOLS = ["ISAC.L", "CNDX.L", "CSPX.L", "FLXC.DE", "VWCG.DE", "ETFBW20TR.WA"]
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))

last_check_time = None
last_check_status = None


def check_prices():
    global last_check_time, last_check_status
    
    try:
        current_time = datetime.now()
        if current_time.hour < 9 or current_time.hour >= 20:
            log_to_file("Outside market hours, skipping check")
            return

        today = datetime.now().strftime('%Y-%m-%d')
        sent_alerts = get_sent_alerts()
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

                log_to_file(f"{symbol}: {current_price} (Change: {change_pct:.2f}%)")
                
                result = {
                    "symbol": symbol,
                    "price": current_price,
                    "change_pct": change_pct,
                    "status": "checked"
                }

                alert_key = f"{symbol}_{today}"

                if change_pct <= -1.5000 and alert_key not in sent_alerts:
                    message = (
                        f"📉 Price Alert: {symbol}\n"
                        f"Current Price: {current_price}\n"
                        f"Change: {change_pct:.4f}%"
                    )
                    send_telegram(message)
                    mark_as_sent(alert_key)
                    result["alert_sent"] = True
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

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "price-drop-tracker"
    }), 200


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/check-prices', methods=['POST'])
def check_prices_endpoint():
    log_to_file("Manual price check triggered via API")
    check_prices()
    
    return jsonify({
        "message": "Price check completed",
        "last_check": last_check_status
    }), 200


@app.route('/status', methods=['GET'])
def status():
    if last_check_status is None:
        return jsonify({
            "status": "no_checks_yet",
            "message": "No price checks have been performed yet"
        }), 200
    
    return jsonify(last_check_status), 200


@app.route('/logs', methods=['GET'])
def get_logs():
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        log_path = f"/var/log/price-drop/{today}.log"
        
        if not os.path.exists(log_path):
            return jsonify({
                "date": today,
                "logs": [],
                "message": "No logs for today"
            }), 200
        
        with open(log_path, 'r') as f:
            logs = f.readlines()
        
        return jsonify({
            "date": today,
            "logs": logs,
            "count": len(logs)
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route('/symbols', methods=['GET'])
def get_symbols():
    return jsonify({
        "symbols": SYMBOLS,
        "count": len(SYMBOLS)
    }), 200


scheduler = BackgroundScheduler()

def scheduled_check():
    check_prices()

scheduler.add_job(
    func=scheduled_check,
    trigger="interval",
    seconds=CHECK_INTERVAL,
    id='price_check_job',
    name='Price Check Job',
    replace_existing=True
)

scheduler.start()
atexit.register(lambda: scheduler.shutdown())


if __name__ == '__main__':
    log_to_file("================================ Flask Service Status: Started ================================")
    app.run(host='0.0.0.0', port=5000, debug=False)
