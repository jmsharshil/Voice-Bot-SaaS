from django.apps import AppConfig


class BotConfig(AppConfig):
    name = 'bot'

    def ready(self):
        import threading
        from .views import auto_resume_suspended_campaigns
        threading.Thread(target=auto_resume_suspended_campaigns, daemon=True).start()
