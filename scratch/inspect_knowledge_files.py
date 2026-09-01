# scratch/inspect_knowledge_files.py
import os
import sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from agents.models import VoiceAgent
from knowledge.models import KnowledgeFile, KnowledgeChunk

def inspect():
    agent = VoiceAgent.objects.filter(name__icontains="Raahi").first()
    print("Agent:", agent.id, agent.name if agent else "None")
    
    kfs = KnowledgeFile.objects.filter(agent=agent)
    print(f"Total KnowledgeFiles for Raahi: {kfs.count()}")
    for kf in kfs:
        chunk_count = KnowledgeChunk.objects.filter(knowledge_file=kf).count()
        print(f"  - ID: {kf.id} | File: {kf.file.name} | Extracted Text Length: {len(kf.extracted_text or '')} | Chunks: {chunk_count}")

if __name__ == "__main__":
    inspect()
