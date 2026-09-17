"""
Management command to rebuild FAISS indexes for all agents.

Usage:
    python manage.py rebuild_faiss_indexes           # all agents
    python manage.py rebuild_faiss_indexes --agent=UUID  # specific agent
"""

from django.core.management.base import BaseCommand
from agents.models import VoiceAgent
from knowledge.models import KnowledgeFile, KnowledgeChunk
from knowledge.services.text_extractor import extract_text
from knowledge.services.chunker import chunk_text
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

    def _ensure_chunks_for_agent(self, agent):
        knowledge_files = KnowledgeFile.objects.filter(agent=agent)
        for kf in knowledge_files:
            existing_chunks = KnowledgeChunk.objects.filter(knowledge_file=kf)
            if not existing_chunks.exists():
                self.stdout.write(f"    📄 Extracting & chunking: {kf.file.name}...")
                try:
                    extracted = extract_text(kf.file)
                    kf.extracted_text = extracted
                    kf.save()

                    chunks = chunk_text(extracted)
                    chunk_objs = [
                        KnowledgeChunk(
                            knowledge_file=kf,
                            content=c_text
                        )
                        for c_text in chunks
                    ]
                    KnowledgeChunk.objects.bulk_create(chunk_objs)
                    self.stdout.write(f"    ✅ Created {len(chunk_objs)} chunks for {kf.file.name}")
                except Exception as e:
                    self.stderr.write(f"    ❌ Error chunking {kf.file.name}: {e}")

    def handle(self, *args, **options):
        agent_id = options["agent"]

        if agent_id:
            try:
                agent = VoiceAgent.objects.get(id=agent_id)
            except VoiceAgent.DoesNotExist:
                self.stderr.write(f"❌ Agent {agent_id} not found")
                return

            self.stdout.write(f"🔄 Rebuilding FAISS index for agent: {agent.name} ({agent.id})")
            self._ensure_chunks_for_agent(agent)
            build_agent_index(agent)
            self.stdout.write(self.style.SUCCESS("✅ Done!"))
        else:
            agents = VoiceAgent.objects.all()
            self.stdout.write(f"🔄 Rebuilding FAISS indexes for {agents.count()} agents...")

            for agent in agents:
                self.stdout.write(f"  → {agent.name} ({agent.id})")
                try:
                    self._ensure_chunks_for_agent(agent)
                    build_agent_index(agent)
                except Exception as e:
                    self.stderr.write(f"  ❌ Failed: {e}")

            self.stdout.write(self.style.SUCCESS(f"✅ All done! {agents.count()} agents processed."))

