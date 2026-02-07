import os
import json
from datetime import datetime

MEMORY_FILE = "/opt/price-drop/alert_thresholds"

def get_alert_thresholds():
    """Pobiera zapisane progi alertów dla dzisiejszego dnia"""
    if not os.path.exists(MEMORY_FILE):
        return {}
    
    try:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
        
        # Sprawdź czy data jest dzisiejsza
        today = datetime.now().strftime('%Y-%m-%d')
        if data.get('date') == today:
            return data.get('thresholds', {})
        else:
            # Nowy dzień - resetuj progi
            return {}
    except:
        return {}

def save_alert_threshold(symbol, threshold):
    """Zapisuje ostatni wysłany próg alertu dla symbolu"""
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    
    today = datetime.now().strftime('%Y-%m-%d')
    data = {'date': today, 'thresholds': {}}
    
    # Wczytaj istniejące dane
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                existing = json.load(f)
            if existing.get('date') == today:
                data['thresholds'] = existing.get('thresholds', {})
        except:
            pass
    
    # Aktualizuj próg dla symbolu
    data['thresholds'][symbol] = threshold
    
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f)

def cleanup_alert_file():
    """Czyści plik alertów o północy (dla nowego dnia)"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                data = json.load(f)
            
            if data.get('date') != today:
                # Nowy dzień - resetuj plik
                os.remove(MEMORY_FILE)
        except:
            pass