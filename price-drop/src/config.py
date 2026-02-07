import os

TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))

ALERT_THRESHOLD_FIRST = -1.0
ALERT_THRESHOLD_STEP = -0.5

MARKET_OPEN_HOUR = 9
MARKET_CLOSE_HOUR = 18

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

LOG_DIR = "/var/log/price-drop"
DATA_DIR = "/opt/price-drop"
ALERT_THRESHOLDS_FILE = f"{DATA_DIR}/alert_thresholds"
