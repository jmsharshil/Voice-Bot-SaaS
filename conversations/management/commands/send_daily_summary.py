from datetime import datetime
from django.core.management.base import BaseCommand
from conversations.services.daily_summary_service import generate_and_send_daily_summary
from conversations.models import DailyCampaignSummaryConfig


class Command(BaseCommand):
    help = "Generates and sends the daily campaign and telephony summary email to configured recipients."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force send even if already sent today or if automated sending is disabled in config.",
        )
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="Target date to summarize in YYYY-MM-DD format (defaults to today in IST).",
        )
        parser.add_argument(
            "--to",
            type=str,
            default=None,
            help="Comma-separated list of recipient emails to send to (overrides config recipients for testing).",
        )
        parser.add_argument(
            "--test",
            action="store_true",
            help="Shortcut for --force. Sends summary immediately to verify email delivery.",
        )
        parser.add_argument(
            "--dummy",
            "--sample",
            action="store_true",
            help="Include realistic dummy/sample campaigns for testing and demonstration.",
        )

    def handle(self, *args, **options):
        force = options["force"] or options["test"]
        date_str = options["date"]
        to_str = options["to"]

        target_date = None
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                self.stderr.write(self.style.ERROR(f"Invalid date format: {date_str}. Expected YYYY-MM-DD."))
                return

        custom_recipients = None
        if to_str:
            import re
            parts = re.split(r"[,;\s]+", to_str)
            custom_recipients = [p.strip() for p in parts if p.strip() and "@" in p]

        config = DailyCampaignSummaryConfig.get_config()
        self.stdout.write(self.style.NOTICE(f"Current Config: Enabled={config.is_enabled}, Time={config.send_time} IST"))
        self.stdout.write(self.style.NOTICE(f"Configured Recipients: {config.get_clean_email_list()}"))

        dummy = options.get("dummy", False)
        self.stdout.write("Generating and sending daily summary email...")
        result = generate_and_send_daily_summary(
            target_date=target_date,
            force=force,
            custom_recipients=custom_recipients,
            dummy=dummy
        )

        status = result.get("status")
        msg = result.get("message")

        if status == "success":
            self.stdout.write(self.style.SUCCESS(f"✅ Success: {msg}"))
            if "recipients" in result:
                self.stdout.write(f"   Delivered to: {', '.join(result['recipients'])}")
        elif status == "skipped":
            self.stdout.write(self.style.WARNING(f"⚠️ Skipped: {msg} (Use --force or --test to send anyway)"))
        else:
            self.stderr.write(self.style.ERROR(f"❌ Error: {msg}"))

