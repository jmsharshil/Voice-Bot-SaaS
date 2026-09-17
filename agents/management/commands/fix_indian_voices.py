from django.core.management.base import BaseCommand
from agents.models import AgentRoleTemplate

INDUSTRY_VOICE_MAP = {
    "healthcare": "en-IN-NeerjaNeural",
    "sales-marketing": "en-IN-PrabhatNeural",
    "education": "en-IN-NeerjaNeural",
    "real-estate": "en-IN-PrabhatNeural",
    "hospitality": "en-IN-NeerjaNeural",
    "customer-service": "en-IN-NeerjaNeural",
    "recruitment": "en-IN-PrabhatNeural",
    "bfsi": "en-IN-PrabhatNeural",
}

class Command(BaseCommand):
    help = "Fix existing role templates to use Indian Azure voices"

    def handle(self, *args, **kwargs):
        updated = 0

        for role in AgentRoleTemplate.objects.select_related("industry"):
            slug = role.industry.slug
            if slug in INDUSTRY_VOICE_MAP:
                new_voice = INDUSTRY_VOICE_MAP[slug]

                if role.default_voice != new_voice:
                    role.default_voice = new_voice
                    role.save(update_fields=["default_voice"])
                    updated += 1
                    self.stdout.write(
                        f"Updated {role.role_name} ({slug}) → {new_voice}"
                    )

        self.stdout.write(
            self.style.SUCCESS(f"Done. Updated {updated} role templates.")
        )