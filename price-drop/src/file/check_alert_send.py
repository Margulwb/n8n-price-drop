import os
import json
from datetime import datetime

MEMORY_FILE = "/opt/price-drop/alert_thresholds"

def get_alert_thresholds():
    if not os.path.exists(MEMORY_FILE):
        return {}
    
    try:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
        
        today = datetime.now().strftime('%Y-%m-%d')
        if data.get('date') == today:
            return data.get('thresholds', {})
        else:
            return {}
    except:
        return {}

def save_alert_threshold(symbol, threshold):
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    
    today = datetime.now().strftime('%Y-%m-%d')
    data = {'date': today, 'thresholds': {}}
    
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                existing = json.load(f)
            if existing.get('date') == today:
                data['thresholds'] = existing.get('thresholds', {})
        except:
            pass
    
    data['thresholds'][symbol] = threshold
    
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f)

def cleanup_alert_file():
    today = datetime.now().strftime('%Y-%m-%d')
    
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                data = json.load(f)
            
            if data.get('date') != today:
                os.remove(MEMORY_FILE)
        except:
            pass