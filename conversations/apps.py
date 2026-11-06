import sys
from django.apps import AppConfig


class ConversationsConfig(AppConfig):
    name = 'conversations'

    def ready(self):
        # Only start scheduler during server runtime, not during management tasks
        is_manage_command = any(arg in sys.argv for arg in ['makemigrations', 'migrate', 'collectstatic', 'check', 'test', 'shell', 'seed_sarvam_agents', 'send_daily_summary'])
        if not is_manage_command:
            try:
                from .services.daily_summary_scheduler import start_daily_summary_scheduler
                start_daily_summary_scheduler()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Could not start daily summary scheduler: {e}")

