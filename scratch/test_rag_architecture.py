# scratch/test_rag_architecture.py
import os
import sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from agents.models import VoiceAgent, AgentRoleTemplate
from knowledge.models import KnowledgeFile, KnowledgeChunk
from knowledge.services.indexer import build_agent_index
from knowledge.services.retriever import retrieve_relevant_chunks

def test_rag():
    print("--- 1. Fetching or Creating Raahi Agent ---")
    agent = VoiceAgent.objects.filter(role_template__role_name__icontains="raahi").first()
    if not agent:
        role = AgentRoleTemplate.objects.filter(role_name__icontains="raahi").first()
        if not role:
            role = AgentRoleTemplate.objects.create(
                role_name="Raahi Triple iEM Advisor",
                strategy_key="raahi_iiiem_strategy",
                system_prompt_template="Test prompt"
            )
        agent = VoiceAgent.objects.create(
            name="Raahi - Triple i E M",
            role_template=role,
            company_name="Triple i E M"
        )
    print(f"Agent ID: {agent.id} | Name: {agent.name}")

    print("\n--- 2. Seeding Test Knowledge Chunks ---")
    kf, _ = KnowledgeFile.objects.get_or_create(
        agent=agent,
        filename="test_iiiem_kb.txt",
        defaults={"file_type": "txt", "status": "processed"}
    )
    
    test_chunks = [
        "ETP (Export Training Plan) is for beginners. The price is 14,999 rupees plus GST for online mode, and 19,999 rupees plus GST for offline mode.",
        "ERP (Export Readiness Plan) costs 34,999 rupees plus GST. It includes ETP foundation plus website setup, digital setup, and export registration support.",
        "EGP (Export Growth Plan) costs 49,999 rupees plus GST. It includes 6 weeks of practical export execution with daily tasks, buyer research, and first 5 shipment handholding support.",
        "Dipak Manohar is the Founder of Triple i E M with 23 plus years of experience in export-import. Manohar International is iiiEM's group company exported to 50 plus countries."
    ]
    
    # Delete old chunks for clean test
    KnowledgeChunk.objects.filter(knowledge_file=kf).delete()
    for idx, text in enumerate(test_chunks):
        KnowledgeChunk.objects.create(
            knowledge_file=kf,
            chunk_index=idx,
            content=text
        )
    print(f"Created {len(test_chunks)} knowledge chunks.")

    print("\n--- 3. Building FAISS Index ---")
    idx_path = build_agent_index(str(agent.id))
    print(f"FAISS Index Built at: {idx_path}")

    print("\n--- 4. Testing RAG Retrieval ---")
    query = "What is the price and details of EGP plan?"
    context = retrieve_relevant_chunks(agent, query)
    print(f"Query  : '{query}'")
    print(f"Context: '{context}'")
    assert "49,999" in context or "EGP" in context, "Expected EGP details in RAG context!"
    print("\n✅ RAG Architecture Verification PASSED!")

if __name__ == "__main__":
    test_rag()
