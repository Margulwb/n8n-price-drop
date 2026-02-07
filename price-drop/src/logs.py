from datetime import datetime, timedelta
import os
import glob

from src.config import LOG_DIR


def log_to_file(message):
    today = datetime.now().strftime('%Y-%m-%d')
    log_path = os.path.join(LOG_DIR, f"{today}.log")
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)
        
    formatted_msg = f"[{timestamp}] {message}"
    with open(log_path, "a") as f:
        f.write(formatted_msg + "\n")
    print(formatted_msg)

def cleanup_old_logs():
    cutoff = datetime.now() - timedelta(days=7)
    files = glob.glob(os.path.join(LOG_DIR, "*.log"))
    for f in files:
        try:
            file_name = os.path.basename(f).replace(".log", "")
            file_date = datetime.strptime(file_name, '%Y-%m-%d')
            if file_date < cutoff:
                os.remove(f)
                log_to_file(f"System: Deleted old log file {file_name}.log")
        except Exception as e:
            log_to_file(f"System: Error during cleanup of {f}: {e}")