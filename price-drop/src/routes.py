import os
from datetime import datetime
from flask import Blueprint, jsonify, render_template

from src.config import SYMBOLS, LOG_DIR
from src.logs import log_to_file
from src.telegram import send_telegram
from src.price_checker import check_prices, get_last_check_status

api = Blueprint('api', __name__)


@api.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "price-drop-tracker"
    }), 200


@api.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@api.route('/check-prices', methods=['POST'])
def check_prices_endpoint():
    log_to_file("Manual price check triggered via API")
    check_prices()
    
    return jsonify({
        "message": "Price check completed",
        "last_check": get_last_check_status()
    }), 200


@api.route('/status', methods=['GET'])
def status():
    last_check_status = get_last_check_status()
    if last_check_status is None:
        return jsonify({
            "status": "no_checks_yet",
            "message": "No price checks have been performed yet"
        }), 200
    
    return jsonify(last_check_status), 200


@api.route('/logs', methods=['GET'])
def get_logs():
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        log_path = f"{LOG_DIR}/{today}.log"
        
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


@api.route('/symbols', methods=['GET'])
def get_symbols():
    return jsonify({
        "symbols": SYMBOLS,
        "count": len(SYMBOLS)
    }), 200


@api.route('/send-status-telegram', methods=['POST'])
def send_status_telegram():
    try:
        last_check_status = get_last_check_status()
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
