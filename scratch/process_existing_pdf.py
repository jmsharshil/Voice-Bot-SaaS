# scratch/process_existing_pdf.py
import os
import sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from agents.models import VoiceAgent
from knowledge.models import KnowledgeFile, KnowledgeChunk
from knowledge.services.text_extractor import extract_text
from knowledge.services.chunker import chunk_text
from knowledge.services.indexer import build_agent_index
from knowledge.services.retriever import retrieve_relevant_chunks

def process_pdf():
    agent = VoiceAgent.objects.filter(name__icontains="Raahi").first()
    print("Processing uploaded PDF for Agent:", agent.id, agent.name)

    kfs = KnowledgeFile.objects.filter(agent=agent)
    for kf in kfs:
        print(f"Processing File ID {kf.id}: {kf.file.name}")
        extracted = extract_text(kf.file)
        kf.extracted_text = extracted
        kf.save()
        print(f"  - Extracted Text Length: {len(extracted)} characters")

        chunks = chunk_text(extracted)
        print(f"  - Generated Chunks: {len(chunks)}")

        KnowledgeChunk.objects.filter(knowledge_file=kf).delete()
        chunk_objs = [
            KnowledgeChunk(
                knowledge_file=kf,
                chunk_index=idx,
                content=c_text
            )
            for idx, c_text in enumerate(chunks)
        ]
        KnowledgeChunk.objects.bulk_create(chunk_objs)

    print("\n--- Building FAISS Vector Index ---")
    idx_path = build_agent_index(str(agent.id))
    print("FAISS Index Built at:", idx_path)

    print("\n--- Testing RAG Retrieval on Uploaded PDF ---")
    queries = [
        "ETP plan ka fee kitna hai?",
        "What is 6 weeks execution support in EGP?",
        "Dipak Manohar ke paas kitna experience hai?",
        "State wise Gujarat petroleum export kitna hai?"
    ]
    for q in queries:
        ctx = retrieve_relevant_chunks(agent, q)
        print(f"\nQ: {q}")
        print(f"RAG Answer Chunk: {ctx[:200]}...")

if __name__ == "__main__":
    process_pdf()
