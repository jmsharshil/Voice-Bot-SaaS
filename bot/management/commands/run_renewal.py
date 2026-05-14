from django.core.management.base import BaseCommand
from bot.services.renewal_service import run_renewal

class Command(BaseCommand):
    help = "Run renewal reminder system"

    def handle(self, *args, **kwargs):
        print("🚀 Running renewal job...")
        run_renewal()
        print("✅ Done sending messages.")