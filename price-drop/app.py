import requests
from datetime import datetime
import os
import logging
from flask import Flask, jsonify, render_template, request
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

from src.file.logs import log_to_file, cleanup_old_logs
from src.file.check_alert_send import get_alert_thresholds, save_alert_threshold, cleanup_alert_file
from src.telegram.send import send_telegram

app = Flask(__name__, template_folder='templates')

log = logging.getLogger('werkzeug')

class HealthCheckFilter(logging.Filter):
    def filter(self, record):
        return '/health' not in record.getMessage()

log.addFilter(HealthCheckFilter())

CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOL_NAMES = {
    "ISAC.L": "MSCI ACWI Globalny",
    "CNDX.L": "NASDAQ 100",
    "CSPX.L": "S&P 500",
    "FLXC.DE": "FTSE China",
    "VWCG.DE": "FTSE Developed Europe",
    "ETFBW20TR.WA": "WIG20",
    "FLXI.DE": "FTSE India",
    "VVSM.DE": "Semiconductor"
}

SYMBOLS = list(SYMBOL_NAMES.keys())
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))
ALERT_THRESHOLD_FIRST = -1.0
ALERT_THRESHOLD_STEP = -0.5

last_check_time = None
last_check_status = None


def get_next_threshold(current_change_pct):
    threshold = ALERT_THRESHOLD_FIRST
    while threshold >= current_change_pct:
        threshold += ALERT_THRESHOLD_STEP
    return threshold - ALERT_THRESHOLD_STEP

def check_prices():
    global last_check_time, last_check_status
    
    try:
        current_time = datetime.now()
        hour = current_time.hour
        if hour < 9 or hour >= 18:
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


@app.route('/send-status-telegram', methods=['POST'])
def send_status_telegram():
    try:
        if last_check_status is None:
            return jsonify({
                "message": "No price data available yet",
                "status_sent": False
            }), 200
        
        results = last_check_status.get('results', [])
        if not results:
            return jsonify({
                "message": "No results to send",
                "status_sent": False
            }), 200
        
        message_lines = ["📊 Price Drop Tracker Status\n"]
        for result in results:
            if result.get('status') == 'checked':
                name = result.get('name', result.get('symbol'))
                price = result.get('price', 'N/A')
                change = result.get('change_pct', 0)
                alert = "🚨" if result.get('alert_sent') else "✓"
                message_lines.append(f"{alert} {name}: ${price} ({change:+.2f}%)")
        
        message = "\n".join(message_lines)
        send_telegram(message)
        log_to_file("Status sent to Telegram via endpoint")
        
        return jsonify({
            "message": "Status sent to Telegram successfully",
            "status_sent": True
        }), 200
    except Exception as e:
        log_to_file(f"Error sending status to Telegram: {e}")
        return jsonify({
            "error": str(e),
            "status_sent": False
        }), 500


scheduler = BackgroundScheduler()

def scheduled_check():
    check_prices()

scheduler.add_job(
    func=scheduled_check,
    trigger="interval",
    seconds=CHECK_INTERVAL,
    id='price_check_job',
    name='Price Check Job',
    replace_existing=True,
    next_run_time=datetime.now()
)

print(f"Starting scheduler with interval {CHECK_INTERVAL}s")
scheduler.start()

def shutdown_scheduler():
    try:
        if scheduler.running:
            scheduler.shutdown()
    except Exception:
        pass

atexit.register(shutdown_scheduler)


if __name__ == '__main__':
    log_to_file("================================ Flask Service Status: Started ================================")
    app.run(host='0.0.0.0', port=5000, debug=False)
