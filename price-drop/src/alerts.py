import os
import json
from datetime import datetime

from src.config import ALERT_THRESHOLDS_FILE


def get_alert_thresholds():
    if not os.path.exists(ALERT_THRESHOLDS_FILE):
        return {}
    
    try:
        with open(ALERT_THRESHOLDS_FILE, "r") as f:
            data = json.load(f)
        
        today = datetime.now().strftime('%Y-%m-%d')
        if data.get('date') == today:
            return data.get('thresholds', {})
        else:
            return {}
    except:
        return {}


def save_alert_threshold(symbol, threshold):
    os.makedirs(os.path.dirname(ALERT_THRESHOLDS_FILE), exist_ok=True)
    
    today = datetime.now().strftime('%Y-%m-%d')
    data = {'date': today, 'thresholds': {}}
    
    if os.path.exists(ALERT_THRESHOLDS_FILE):
        try:
            with open(ALERT_THRESHOLDS_FILE, "r") as f:
                existing = json.load(f)
            if existing.get('date') == today:
                data['thresholds'] = existing.get('thresholds', {})
        except:
            pass
    
    data['thresholds'][symbol] = threshold
    
    with open(ALERT_THRESHOLDS_FILE, "w") as f:
        json.dump(data, f)


def cleanup_alert_file():
    today = datetime.now().strftime('%Y-%m-%d')
    
    if os.path.exists(ALERT_THRESHOLDS_FILE):
        try:
            with open(ALERT_THRESHOLDS_FILE, "r") as f:
                data = json.load(f)
            
            if data.get('date') != today:
                os.remove(ALERT_THRESHOLDS_FILE)
        except:
            pass