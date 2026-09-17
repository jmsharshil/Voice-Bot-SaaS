# # from knowledge.models import KnowledgeChunk


# # def retrieve_relevant_chunks(agent, query, limit=3):
# #     chunks = KnowledgeChunk.objects.filter(
# #         knowledge_file__agent=agent
# #     )[:limit]

# #     return "\n\n".join([c.content for c in chunks])















# from knowledge.models import KnowledgeChunk
# from conversations.services.azure_openai_service import generate_response
# import json
# import re


# # def retrieve_relevant_chunks(agent, query, limit=3):
# #     chunks = KnowledgeChunk.objects.filter(
# #         knowledge_file__agent=agent
# #     )

# #     chunk_map = {str(i): chunk.content for i, chunk in enumerate(chunks)}

# #     # Prepare chunk summary for GPT
# #     chunk_list_text = "\n\n".join(
# #         [f"{i}: {chunk.content[:300]}" for i, chunk in enumerate(chunks)]
# #     )

# #     retrieval_prompt =  f"""
# # You are a retrieval system.

# # From the list of document chunks below,
# # select the chunk numbers that best answer the user question.

# # IMPORTANT:
# # - Return ONLY a valid JSON list.
# # - Do NOT explain.
# # - Do NOT write text.
# # - Do NOT wrap in markdown.
# # - Example valid output: [1, 3]

# # User Question:
# # {query}

# # Chunks:
# # {chunk_list_text}
# # """

# #     response = generate_response("You are a retrieval system.", retrieval_prompt)

# #     try:
# #         json_text = re.search(r"\[.*?\]", response).group()
# #         indexes = json.loads(json_text)
# #     except:
# #         indexes = []

# #     selected_chunks = [
# #         chunk_map[str(i)] for i in indexes if str(i) in chunk_map
# #     ]

# #     return "\n\n".join(selected_chunks[:limit])




# STOP_WORDS = {
#     "what", "is", "are", "the", "a", "an", "in", "on", "of", "for", "to",
#     "and", "or", "does", "do", "how", "much", "many", "please", "tell",
#     "me", "about", "give", "show", "list", "explain"
# }

# NUMERIC_HINT_WORDS = {
#     "fee", "fees", "cost", "price", "amount",
#     "seat", "seats", "intake", "quota",
#     "aiq", "gq", "mq", "nri"
# }


# # -------------------------
# # Utility functions
# # -------------------------

# def normalize(text: str) -> str:
#     """
#     Normalize text for matching:
#     - lowercase
#     - remove symbols except numbers and $
#     """
#     return re.sub(r"[^a-z0-9$ ]+", " ", text.lower())


# def extract_keywords(query: str):
#     normalized = normalize(query)
#     return [
#         w for w in normalized.split()
#         if w not in STOP_WORDS and len(w) > 2
#     ]


# def is_numeric_query(query: str) -> bool:
#     q = query.lower()
#     return any(word in q for word in NUMERIC_HINT_WORDS) or any(
#         char.isdigit() for char in q
#     )


# # -------------------------
# # Main Retriever
# # -------------------------

# # def retrieve_relevant_chunks(agent, query, limit=5):
# #     """
# #     Returns concatenated relevant document chunks.
# #     If nothing relevant is found, returns empty string.
# #     """

# #     chunks = KnowledgeChunk.objects.filter(
# #         knowledge_file__agent=agent
# #     )

# #     if not chunks.exists():
# #         return ""

# #     keywords = extract_keywords(query)
# #     numeric_query = is_numeric_query(query)

# #     # --------------------------------------------------
# #     # STEP 1: Keyword + Score-based Retrieval (Primary)
# #     # --------------------------------------------------

# #     scored_chunks = []

# #     for chunk in chunks:
# #         content = chunk.content
# #         normalized_content = normalize(content)

# #         score = 0

# #         # keyword matching
# #         for kw in keywords:
# #             if kw in normalized_content:
# #                 score += 2

# #         # numeric relevance boost
# #         if numeric_query:
# #             digit_count = sum(c.isdigit() for c in content)
# #             score += min(digit_count, 10)

# #         # college-name boost
# #         if "," in content and any(k in normalized_content for k in keywords):
# #             score += 2

# #         if score > 0:
# #             scored_chunks.append((score, content))

# #     scored_chunks.sort(key=lambda x: x[0], reverse=True)

# #     if scored_chunks:
# #         return "\n\n".join(
# #             [c for _, c in scored_chunks[:limit]]
# #         )

# #     # --------------------------------------------------
# #     # STEP 2: STRICT LLM FALLBACK (NO GUESSING)
# #     # --------------------------------------------------

# #     chunk_map = {
# #         str(i): chunk.content
# #         for i, chunk in enumerate(chunks)
# #     }

# #     chunk_preview = "\n\n".join(
# #         f"{i}: {chunk.content[:400]}"
# #         for i, chunk in enumerate(chunks)
# #     )

# #     retrieval_prompt = f"""
# # You are a STRICT document retrieval system.

# # Rules:
# # - Select chunks ONLY if they clearly contain the answer
# # - If the answer is NOT present, return []
# # - Do NOT guess or infer
# # - Return ONLY a JSON array like [0, 2]

# # User Question:
# # {query}

# # Document Chunks:
# # {chunk_preview}
# # """

# #     response = generate_response(
# #     "You retrieve document chunks only.",
# #     retrieval_prompt
# #     )

# #     indexes = []

# #     try:
# #         match = re.search(r"\[[0-9,\s]*\]", response)
# #         if match:
# #             indexes = json.loads(match.group())
# #     except Exception:
# #         indexes = []

# #     selected_chunks = [
# #         chunk_map[str(i)]
# #         for i in indexes
# #         if str(i) in chunk_map
# #     ]

# #     if not selected_chunks:
# #         return ""




# def retrieve_relevant_chunks(agent, query, limit=5):

#     import time  # ✅ added
#     rag_start = time.time()  # ✅ start timer

#     """
#     Returns concatenated relevant document chunks.
#     If nothing relevant is found, returns fallback chunks.
#     """

#     chunks = KnowledgeChunk.objects.filter(
#         knowledge_file__agent=agent
#     )

#     if not chunks.exists():
#         print("⏱ RAG Time:", time.time() - rag_start)
#         return ""

#     # Normalize keywords
#     keywords = [k.lower() for k in extract_keywords(query)]
#     numeric_query = is_numeric_query(query)

#     # --------------------------------------------------
#     # STEP 1: Keyword + Score-based Retrieval (Primary)
#     # --------------------------------------------------

#     scored_chunks = []

#     for chunk in chunks:
#         content = chunk.content
#         normalized_content = normalize(content).lower()

#         score = 0

#         # keyword matching
#         for kw in keywords:
#             if kw in normalized_content:
#                 score += 2

#         # numeric relevance boost
#         if numeric_query:
#             digit_count = sum(c.isdigit() for c in content)
#             score += min(digit_count, 10)

#         # location / comma boost
#         if "," in content and any(k in normalized_content for k in keywords):
#             score += 2

#         if score > 0:
#             scored_chunks.append((score, content))

#     # Sort by score
#     scored_chunks.sort(key=lambda x: x[0], reverse=True)

#     if scored_chunks:
#         print("⏱ RAG Time:", time.time() - rag_start)
#         return "\n\n".join(
#             [c for _, c in scored_chunks[:limit]]
#         )

#     # --------------------------------------------------
#     # STEP 2: STRICT LLM FALLBACK (NO GUESSING)
#     # --------------------------------------------------

#     chunk_map = {
#         str(i): chunk.content
#         for i, chunk in enumerate(chunks)
#     }

#     chunk_preview = "\n\n".join(
#         f"{i}: {chunk.content[:400]}"
#         for i, chunk in enumerate(chunks)
#     )

#     retrieval_prompt = f"""
# You are a STRICT document retrieval system.

# Rules:
# - Select chunks ONLY if they clearly contain the answer
# - If the answer is NOT present, return []
# - Do NOT guess or infer
# - Return ONLY a JSON array like [0, 2]

# User Question:
# {query}

# Document Chunks:
# {chunk_preview}
# """

#     response = generate_response(
#         "You retrieve document chunks only.",
#         retrieval_prompt
#     )

#     indexes = []

#     try:
#         match = re.search(r"\[[0-9,\s]*\]", response)
#         if match:
#             indexes = json.loads(match.group())
#     except Exception:
#         indexes = []

#     selected_chunks = [
#         chunk_map[str(i)]
#         for i in indexes
#         if str(i) in chunk_map
#     ]

#     if not selected_chunks:
#         print("⏱ RAG Time:", time.time() - rag_start)
#         return ""







# from knowledge.models import KnowledgeChunk


# def retrieve_relevant_chunks(agent, query, limit=3):
#     chunks = KnowledgeChunk.objects.filter(
#         knowledge_file__agent=agent
#     )[:limit]

#     return "\n\n".join([c.content for c in chunks])















from knowledge.models import KnowledgeChunk
from conversations.services.azure_openai_service import generate_response
import json
import re


# def retrieve_relevant_chunks(agent, query, limit=3):
#     chunks = KnowledgeChunk.objects.filter(
#         knowledge_file__agent=agent
#     )

#     chunk_map = {str(i): chunk.content for i, chunk in enumerate(chunks)}

#     # Prepare chunk summary for GPT
#     chunk_list_text = "\n\n".join(
#         [f"{i}: {chunk.content[:300]}" for i, chunk in enumerate(chunks)]
#     )

#     retrieval_prompt =  f"""
# You are a retrieval system.

# From the list of document chunks below,
# select the chunk numbers that best answer the user question.

# IMPORTANT:
# - Return ONLY a valid JSON list.
# - Do NOT explain.
# - Do NOT write text.
# - Do NOT wrap in markdown.
# - Example valid output: [1, 3]

# User Question:
# {query}

# Chunks:
# {chunk_list_text}
# """

#     response = generate_response("You are a retrieval system.", retrieval_prompt)

#     try:
#         json_text = re.search(r"\[.*?\]", response).group()
#         indexes = json.loads(json_text)
#     except:
#         indexes = []

#     selected_chunks = [
#         chunk_map[str(i)] for i in indexes if str(i) in chunk_map
#     ]

#     return "\n\n".join(selected_chunks[:limit])




STOP_WORDS = {
    "what", "is", "are", "the", "a", "an", "in", "on", "of", "for", "to",
    "and", "or", "does", "do", "how", "much", "many", "please", "tell",
    "me", "about", "give", "show", "list", "explain"
}

NUMERIC_HINT_WORDS = {
    "fee", "fees", "cost", "price", "amount",
    "seat", "seats", "intake", "quota",
    "aiq", "gq", "mq", "nri"
}


# -------------------------
# Utility functions
# -------------------------

def normalize(text: str) -> str:
    """
    Normalize text for matching:
    - lowercase
    - remove symbols except numbers and $
    """
    return re.sub(r"[^a-z0-9$ ]+", " ", text.lower())


def extract_keywords(query: str):
    normalized = normalize(query)
    return [
        w for w in normalized.split()
        if w not in STOP_WORDS and len(w) > 2
    ]


def is_numeric_query(query: str) -> bool:
    q = query.lower()
    return any(word in q for word in NUMERIC_HINT_WORDS) or any(
        char.isdigit() for char in q
    )


# -------------------------
# Main Retriever
# -------------------------

# def retrieve_relevant_chunks(agent, query, limit=5):
#     """
#     Returns concatenated relevant document chunks.
#     If nothing relevant is found, returns empty string.
#     """

#     chunks = KnowledgeChunk.objects.filter(
#         knowledge_file__agent=agent
#     )

#     if not chunks.exists():
#         return ""

#     keywords = extract_keywords(query)
#     numeric_query = is_numeric_query(query)

#     # --------------------------------------------------
#     # STEP 1: Keyword + Score-based Retrieval (Primary)
#     # --------------------------------------------------

#     scored_chunks = []

#     for chunk in chunks:
#         content = chunk.content
#         normalized_content = normalize(content)

#         score = 0

#         # keyword matching
#         for kw in keywords:
#             if kw in normalized_content:
#                 score += 2

#         # numeric relevance boost
#         if numeric_query:
#             digit_count = sum(c.isdigit() for c in content)
#             score += min(digit_count, 10)

#         # college-name boost
#         if "," in content and any(k in normalized_content for k in keywords):
#             score += 2

#         if score > 0:
#             scored_chunks.append((score, content))

#     scored_chunks.sort(key=lambda x: x[0], reverse=True)

#     if scored_chunks:
#         return "\n\n".join(
#             [c for _, c in scored_chunks[:limit]]
#         )

#     # --------------------------------------------------
#     # STEP 2: STRICT LLM FALLBACK (NO GUESSING)
#     # --------------------------------------------------

#     chunk_map = {
#         str(i): chunk.content
#         for i, chunk in enumerate(chunks)
#     }

#     chunk_preview = "\n\n".join(
#         f"{i}: {chunk.content[:400]}"
#         for i, chunk in enumerate(chunks)
#     )

#     retrieval_prompt = f"""
# You are a STRICT document retrieval system.

# Rules:
# - Select chunks ONLY if they clearly contain the answer
# - If the answer is NOT present, return []
# - Do NOT guess or infer
# - Return ONLY a JSON array like [0, 2]

# User Question:
# {query}

# Document Chunks:
# {chunk_preview}
# """

#     response = generate_response(
#     "You retrieve document chunks only.",
#     retrieval_prompt
#     )

#     indexes = []

#     try:
#         match = re.search(r"\[[0-9,\s]*\]", response)
#         if match:
#             indexes = json.loads(match.group())
#     except Exception:
#         indexes = []

#     selected_chunks = [
#         chunk_map[str(i)]
#         for i in indexes
#         if str(i) in chunk_map
#     ]

#     if not selected_chunks:
#         return ""


GREETING_PATTERNS = {
    "hello", "hi", "hey", "helo", "hii",
    "good morning", "good afternoon", "good evening",
    "namaste", "namaskar", "haan", "han", "जी हाँ", "जी", "हां", "बोलिए",
    "ha", "haa", "boliye", "yes", "ok", "okay", "acha", "achha",
    "abhi toh", "abhi nahi", "nahi abhi", "time hai", "theek hai", "thik hai"
}

def retrieve_relevant_chunks(agent, query, limit=5):

    import time
    import re as _re
    rag_start = time.time()

    # Strip Devanagari/Hindi terminal punctuation before matching
    normalized_query = _re.sub(r'[\u0964\u0965!?,.\'"]+', '', query).lower().strip()
    word_count = len(normalized_query.split())

    # Fast-exit: conversational opener or very short query — no RAG needed
    # Saves ~335ms CPU embedding for phrases that will never match a chunk
    if normalized_query in GREETING_PATTERNS or word_count <= 3:
        print(f"[RAG] Short/greeting ({word_count}w) — skipping RAG")
        return ""

    """
    Returns concatenated relevant document chunks.
    If nothing relevant is found, returns fallback chunks.
    """

    chunks = KnowledgeChunk.objects.filter(
        knowledge_file__agent=agent
    )

    if not chunks.exists():
        print("[RAG] No chunks found for agent")
        print("[RAG] Time:", round((time.time() - rag_start) * 1000), "ms")
        return ""

    # --------------------------------------------------
    # STEP 0: FAISS Semantic Search (Fastest + Most Accurate)
    # --------------------------------------------------

    try:
        from knowledge.services.indexer import generate_embedding, load_agent_index
        import numpy as np

        agent_id = str(agent.id)
        t0 = time.time()
        index, chunk_ids = load_agent_index(agent_id)

        if index is not None and index.ntotal > 0:
            load_ms = round((time.time() - t0) * 1000)

            # Generate query embedding
            t_embed = time.time()
            query_vector = generate_embedding(query).reshape(1, -1)
            embed_ms = round((time.time() - t_embed) * 1000)

            # FAISS search
            t_search = time.time()
            k = min(limit, index.ntotal)
            distances, indices = index.search(query_vector, k)
            search_ms = round((time.time() - t_search) * 1000)

            # Filter by threshold
            SIMILARITY_THRESHOLD = 0.25
            faiss_results = []

            print(f"\n{'='*60}")
            print(f"[RAG] Query: \"{query}\"")
            print(f"[RAG] Agent: {agent.name} ({agent_id})")
            print(f"[RAG] FAISS: {index.ntotal} vectors | load={load_ms}ms | embed={embed_ms}ms | search={search_ms}ms")
            print(f"[RAG] --- Semantic Search Results (threshold={SIMILARITY_THRESHOLD}) ---")

            for i in range(k):
                score = float(distances[0][i])
                idx = int(indices[0][i])

                if idx < 0 or idx >= len(chunk_ids):
                    continue

                chunk_id = int(chunk_ids[idx])
                status = "MATCH" if score >= SIMILARITY_THRESHOLD else "BELOW"
                print(f"  [{i+1}] score={score:.4f} | chunk_id={chunk_id} | {status}")

                if score >= SIMILARITY_THRESHOLD:
                    faiss_results.append(chunk_id)

            if faiss_results:
                # Fetch matched chunks from DB
                matched = KnowledgeChunk.objects.filter(id__in=faiss_results)
                chunk_map_faiss = {c.id: c.content for c in matched}
                selected = [chunk_map_faiss[cid] for cid in faiss_results if cid in chunk_map_faiss]

                total_ms = round((time.time() - rag_start) * 1000)
                print(f"[RAG] Result: {len(selected)} chunks via FAISS semantic search")
                print(f"[RAG] Total: {total_ms}ms")
                print(f"{'='*60}\n")
                return "\n\n".join(selected)
            else:
                print(f"[RAG] FAISS: no match above threshold, falling back to keyword search...")
                print(f"{'='*60}")
        else:
            print("[RAG] No FAISS index found, using keyword search...")

    except Exception as e:
        print(f"[RAG] FAISS error ({e}), falling back to keyword search...")

    # --------------------------------------------------
    # STEP 1: Keyword + Score-based Retrieval (Primary)
    # --------------------------------------------------

    # Normalize keywords
    keywords = [k.lower() for k in extract_keywords(query)]
    numeric_query = is_numeric_query(query)

    scored_chunks = []

    for chunk in chunks:
        content = chunk.content
        normalized_content = normalize(content).lower()

        score = 0

        # keyword matching
        for kw in keywords:
            if kw in normalized_content:
                score += 2

        # numeric relevance boost
        if numeric_query:
            digit_count = sum(c.isdigit() for c in content)
            score += min(digit_count, 10)

        # location / comma boost
        if "," in content and any(k in normalized_content for k in keywords):
            score += 2

        if score > 0:
            scored_chunks.append((score, content))

    # Sort by score
    scored_chunks.sort(key=lambda x: x[0], reverse=True)

    if scored_chunks:
        print("[RAG] Result: keyword match found |", round((time.time() - rag_start) * 1000), "ms")
        return "\n\n".join(
            [c for _, c in scored_chunks[:limit]]
        )

    # ⚡ STEP 2: Skip LLM fallback — saves 1-2s when FAISS + keyword both miss
    # The main LLM will still answer from its training knowledge
    print("[RAG] No match (FAISS + keyword) |", round((time.time() - rag_start) * 1000), "ms")
    return ""