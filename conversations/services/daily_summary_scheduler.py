import time
import logging
import threading
from datetime import datetime
from zoneinfo import ZoneInfo
from django.db import close_old_connections
from django.utils import timezone

logger = logging.getLogger(__name__)
IST_TZ = ZoneInfo("Asia/Kolkata")

_SCHEDULER_STARTED = False
_SCHEDULER_LOCK = threading.Lock()


def _daily_summary_worker():
    """
    Background worker loop that runs continuously.
    Wakes up every 60 seconds, checks if current time in IST has reached the configured
    send_time (e.g. 20:00 / 8:00 PM), and triggers the daily summary email if not yet sent today.
    """
    logger.info("⏳ [DAILY SUMMARY SCHEDULER]: Starting background daily email summary worker...")
    print("⏳ [DAILY SUMMARY SCHEDULER]: Starting background daily email summary worker...")

    while True:
        try:
            time.sleep(60)

            # Avoid holding open connections across sleep
            close_old_connections()

            from conversations.models import DailyCampaignSummaryConfig
            from conversations.services.daily_summary_service import generate_and_send_daily_summary

            config = DailyCampaignSummaryConfig.get_config()
            if not config.is_enabled:
                continue

            now_ist = timezone.localtime(timezone.now(), IST_TZ)
            today_date = now_ist.date()

            # If already sent for today, wait until tomorrow
            if config.last_sent_date == today_date:
                continue

            # Parse configured send_time (e.g. "20:00")
            send_time_str = str(config.send_time or "20:00").strip()
            try:
                parts = send_time_str.split(":")
                target_hour = int(parts[0])
                target_minute = int(parts[1]) if len(parts) > 1 else 0
            except Exception:
                target_hour = 20
                target_minute = 0

            # Check if current IST time is at or past target send time
            if now_ist.hour > target_hour or (now_ist.hour == target_hour and now_ist.minute >= target_minute):
                logger.info(f"⏰ [DAILY SUMMARY SCHEDULER]: Scheduled time reached ({send_time_str} IST). Triggering daily summary email for {today_date}...")
                print(f"⏰ [DAILY SUMMARY SCHEDULER]: Scheduled time reached ({send_time_str} IST). Sending summary for {today_date}...")
                
                result = generate_and_send_daily_summary(target_date=today_date, force=False)
                logger.info(f"📊 [DAILY SUMMARY SCHEDULER RESULT]: {result}")
                print(f"📊 [DAILY SUMMARY SCHEDULER RESULT]: {result}")

        except Exception as e:
            close_old_connections()
            logger.error(f"❌ [DAILY SUMMARY SCHEDULER ERROR]: {e}", exc_info=True)


def start_daily_summary_scheduler():
    """
    Starts the daily summary scheduler thread once per process.
    Safe to call multiple times (idempotent).
    """
    global _SCHEDULER_STARTED
    with _SCHEDULER_LOCK:
        if not _SCHEDULER_STARTED:
            _SCHEDULER_STARTED = True
            t = threading.Thread(target=_daily_summary_worker, daemon=True, name="DailySummaryScheduler")
            t.start()
            logger.info("🚀 [DAILY SUMMARY SCHEDULER]: Thread launched successfully.")

