import os

MEMORY_FILE = "/opt/price-drop/last_alerts"

def get_sent_alerts():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return f.read().splitlines()
    return []

def mark_as_sent(symbol_date):
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, "a") as f:
        f.write(f"{symbol_date}\n")