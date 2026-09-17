"""
Management command: seed_sarvam_agents
Run: python manage.py seed_sarvam_agents

Seeds the SarvamAgent table with the Raahi (iiiEM) agent from .env values.
Run this ONCE after the initial migration to populate the default agent.
After that, add new agents via Django Admin > Sarvam Agents > Add.
"""
import os
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seeds the SarvamAgent table with Raahi (iiiEM) from .env credentials"

    def handle(self, *args, **kwargs):
        from conversations.models import SarvamAgent

        org_id = os.getenv("SARVAM_ORG_ID", "")
        workspace_id = os.getenv("SARVAM_WORKSPACE_ID", "")
        app_id = os.getenv("SARVAM_AGENT_ID", "")
        api_key = os.getenv("SARVAM_AGENT_API_KEY", "")
        connection_id = os.getenv("SARVAM_CONNECTION_ID", "")
        agent_phone = os.getenv("SARVAM_AGENT_PHONE_NUMBER", "+917971414121")
        domain = os.getenv("MY_PUBLIC_DOMAIN", "")

        agent, created = SarvamAgent.objects.get_or_create(
            slug="raahi-iiiem",
            defaults={
                "name": "Raahi - iiiEM",
                "description": "iiiEM Export Import Training Institute - Export-Import Senior Counsellor and Advisor",
                "org_id": org_id,
                "workspace_id": workspace_id,
                "app_id": app_id,
                "api_key": api_key,
                "connection_id": connection_id,
                "agent_phone": agent_phone,
                "webhook_domain": domain,
                "is_active": True,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(
                f"Created SarvamAgent: '{agent.name}' (slug={agent.slug})\n"
                f"   Dashboard URL: /api/sarvam/raahi-iiiem/leads/\n"
                f"   Agent Phone:   {agent.agent_phone}\n"
                f"   App ID:        {agent.app_id}"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"SarvamAgent 'raahi-iiiem' already exists. Skipped creation.\n"
                f"   To update, go to Django Admin > Sarvam Agents > raahi-iiiem > Edit"
            ))

        self.stdout.write("\nTo add a NEW Sarvam agent:")
        self.stdout.write("   1. Go to Django Admin > Conversations > Sarvam Agents > Add")
        self.stdout.write("   2. Fill in name, slug, and the new agent's Sarvam credentials")
        self.stdout.write("   3. Dashboard auto-appears at: /api/sarvam/<slug>/leads/")
