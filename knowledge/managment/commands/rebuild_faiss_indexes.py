"""
Management command to rebuild FAISS indexes for all agents.

Usage:
    python manage.py rebuild_faiss_indexes           # all agents
    python manage.py rebuild_faiss_indexes --agent=UUID  # specific agent
"""

from django.core.management.base import BaseCommand
from agents.models import VoiceAgent
from knowledge.services.indexer import build_agent_index


class Command(BaseCommand):
    help = "Rebuild FAISS vector indexes for all agents (or a specific agent)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--agent",
            type=str,
            default=None,
            help="Specific agent UUID to rebuild. If omitted, rebuilds all.",
        )

    def handle(self, *args, **options):
        agent_id = options["agent"]

        if agent_id:
            try:
                agent = VoiceAgent.objects.get(id=agent_id)
            except VoiceAgent.DoesNotExist:
                self.stderr.write(f"❌ Agent {agent_id} not found")
                return

            self.stdout.write(f"🔄 Rebuilding FAISS index for agent: {agent.name} ({agent.id})")
            build_agent_index(agent)
            self.stdout.write(self.style.SUCCESS("✅ Done!"))
        else:
            agents = VoiceAgent.objects.all()
            self.stdout.write(f"🔄 Rebuilding FAISS indexes for {agents.count()} agents...")

            for agent in agents:
                self.stdout.write(f"  → {agent.name} ({agent.id})")
                try:
                    build_agent_index(agent)
                except Exception as e:
                    self.stderr.write(f"  ❌ Failed: {e}")

            self.stdout.write(self.style.SUCCESS(f"✅ All done! {agents.count()} agents processed."))