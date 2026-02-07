import atexit
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

from src.config import CHECK_INTERVAL
from src.price_checker import check_prices

scheduler = BackgroundScheduler()


def start_scheduler():
    scheduler.add_job(
        func=check_prices,
        trigger="interval",
        seconds=CHECK_INTERVAL,
        id='price_check_job',
        name='Price Check Job',
        replace_existing=True,
        next_run_time=datetime.now()
    )
    
    print(f"Starting scheduler with interval {CHECK_INTERVAL}s")
    scheduler.start()
    atexit.register(shutdown_scheduler)


def shutdown_scheduler():
    try:
        if scheduler.running:
            scheduler.shutdown()
    except Exception:
        pass
