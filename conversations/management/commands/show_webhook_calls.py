from django.core.management.base import BaseCommand
from conversations.models import SarvamCallRecord


class Command(BaseCommand):
    help = "Display recent third-party/Kylas webhook calls with their matched City and Voice Agent."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Number of recent calls to display (default: 10)",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        records = (
            SarvamCallRecord.objects.filter(call_type__icontains="Webhook")
            .select_related("sarvam_agent")
            .order_by("-id")[:limit]
        )

        if not records:
            # Fallback to any recent calls if none marked Webhook yet
            records = (
                SarvamCallRecord.objects.select_related("sarvam_agent")
                .order_by("-id")[:limit]
            )

        self.stdout.write("\n" + "=" * 90)
        self.stdout.write("📞 RECENT THIRD-PARTY / KYLAS CALLS (CITY TO AGENT RESOLUTION)")
        self.stdout.write("=" * 90)

        header = f"{'ID':<6} | {'User / Candidate':<22} | {'Phone':<14} | {'City Matched':<14} | {'Voice Agent':<20} | {'Status':<10}"
        self.stdout.write(header)
        self.stdout.write("-" * 90)

        for r in records:
            summary = r.summary if isinstance(r.summary, dict) else {}
            city = summary.get("detected_city")
            if not city:
                raw_payload = summary.get("received_payload") or {}
                entity = raw_payload.get("entity") or {}
                camp = entity.get("campaign")
                city = camp.get("value") if isinstance(camp, dict) else entity.get("city") or "-"

            agent_name = r.sarvam_agent.name if r.sarvam_agent else "Unassigned"
            candidate = (r.candidate_name or "Unknown")[:21]
            phone = (r.phone_number or "-")[:13]
            city_display = str(city or "-")[:13]
            status = (r.status or "-")[:9]

            row = f"{r.id:<6} | {candidate:<22} | {phone:<14} | {city_display:<14} | {agent_name:<20} | {status:<10}"
            self.stdout.write(row)

        self.stdout.write("-" * 90 + "\n")

