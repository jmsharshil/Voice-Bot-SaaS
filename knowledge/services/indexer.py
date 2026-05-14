# """
# FAISS Vector Index Manager for Knowledge Base RAG.

# Uses sentence-transformers () for embeddings — runs locally, no API cost.

# Handles:
# - Generating embeddings via sentence-transformers
# - Building / loading / saving per-agent FAISS indexes
# - Adding new chunks to an existing index
# """
# import os
# os.environ["TOKENIZERS_PARALLELISM"] = "false"
# import os
# import numpy as np
# import faiss
# import time
# from django.conf import settings
# from sentence_transformers import SentenceTransformer
# import threading


# # ── Model (loaded once, reused across calls) ──────────────────
# _model = None
# _model_lock = threading.Lock()
# MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
# EMBEDDING_DIM = 384  #  produces 384-dim vectors


# def _get_model():
#     global _model
#     with _model_lock:
#         if _model is None:
#             print(f"[LOADING] Embedding model: {MODEL_NAME}...")
#             # Load from local cache (no HuggingFace HTTP calls = instant)
#             # Falls back to online download only if model isn't cached yet
#             try:
#                 _model = SentenceTransformer(MODEL_NAME, local_files_only=True)
#             except Exception:
#                 print("[DOWNLOADING] Model not cached, downloading from HuggingFace...")
#                 _model = SentenceTransformer(MODEL_NAME)
#             print("[OK] Embedding model loaded")
#     return _model


# # ── Paths ─────────────────────────────────────────────────────

# def _index_dir(agent_id: str) -> str:
#     """Return the directory where this agent's FAISS index lives."""
#     path = os.path.join(settings.MEDIA_ROOT, "faiss_indexes", str(agent_id))
#     os.makedirs(path, exist_ok=True)
#     return path


# def _index_path(agent_id: str) -> str:
#     return os.path.join(_index_dir(agent_id), "index.faiss")


# def _ids_path(agent_id: str) -> str:
#     return os.path.join(_index_dir(agent_id), "chunk_ids.npy")


# # ── Embedding Generation ─────────────────────────────────────

# def generate_embedding(text: str) -> np.ndarray:
#     """Generate a single embedding vector for the given text."""
#     model = _get_model()
#     vector = model.encode(text, normalize_embeddings=True)
#     return np.array(vector, dtype=np.float32)


# def generate_embeddings_batch(texts: list) -> np.ndarray:
#     """Generate embeddings for a batch of texts."""
#     model = _get_model()
#     vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=len(texts) > 50)
#     return np.array(vectors, dtype=np.float32)


# # ── FAISS Index Management ────────────────────────────────────

# def build_agent_index(agent):
#     """
#     Build (or rebuild) the FAISS index for an agent from all their KnowledgeChunks.
#     Called by the management command and on first upload.
#     """
#     from knowledge.models import KnowledgeChunk

#     start = time.time()
#     agent_id = str(agent.id)

#     chunks = list(
#         KnowledgeChunk.objects.filter(
#             knowledge_file__agent=agent
#         ).values_list("id", "content")
#     )

#     if not chunks:
#         print(f"[!] No chunks found for agent {agent_id}")
#         return

#     chunk_ids = [c[0] for c in chunks]
#     chunk_texts = [c[1] for c in chunks]

#     print(f"[LOADING] Generating embeddings for {len(chunk_texts)} chunks...")
#     vectors = generate_embeddings_batch(chunk_texts)

#     # Save embeddings back to DB
#     for i, chunk_id in enumerate(chunk_ids):
#         KnowledgeChunk.objects.filter(id=chunk_id).update(
#             embedding=vectors[i].tobytes()
#         )

#     # Build FAISS index
#     index = faiss.IndexFlatIP(EMBEDDING_DIM)  # Inner product = cosine on normalized vectors
#     index.add(vectors)

#     # Save index + chunk ID mapping
#     faiss.write_index(index, _index_path(agent_id))
#     np.save(_ids_path(agent_id), np.array(chunk_ids))

#     elapsed = round(time.time() - start, 2)
#     print(f"[OK] FAISS index built for agent {agent_id}: {len(chunk_ids)} chunks in {elapsed}s")


# def load_agent_index(agent_id: str):
#     """
#     Load the FAISS index and chunk ID mapping for an agent.
#     Returns (index, chunk_ids) or (None, None) if no index exists.
#     """
#     idx_path = _index_path(agent_id)
#     ids_path = _ids_path(agent_id)

#     if not os.path.exists(idx_path) or not os.path.exists(ids_path):
#         return None, None

#     index = faiss.read_index(idx_path)
#     chunk_ids = np.load(ids_path)
#     return index, chunk_ids


# def add_chunks_to_index(agent, chunk_objects):
#     """
#     Embed new chunks and add them to the existing FAISS index.
#     If no index exists yet, build one from scratch.

#     chunk_objects: list of KnowledgeChunk instances (already saved to DB).
#     """
#     agent_id = str(agent.id)

#     if not chunk_objects:
#         return

#     # Generate embeddings for new chunks
#     texts = [c.content for c in chunk_objects]
#     vectors = generate_embeddings_batch(texts)

#     # Save embeddings to DB
#     for i, chunk in enumerate(chunk_objects):
#         chunk.embedding = vectors[i].tobytes()
#         chunk.save(update_fields=["embedding"])

#     # Load or create index
#     index, existing_ids = load_agent_index(agent_id)

#     if index is None:
#         # First upload — create new index
#         index = faiss.IndexFlatIP(EMBEDDING_DIM)
#         existing_ids = np.array([], dtype=np.int64)

#     # Add new vectors
#     index.add(vectors)

#     # Append new chunk IDs
#     new_ids = np.array([c.id for c in chunk_objects], dtype=np.int64)
#     all_ids = np.concatenate([existing_ids, new_ids])

#     # Save
#     faiss.write_index(index, _index_path(agent_id))
#     np.save(_ids_path(agent_id), all_ids)

#     print(f"[OK] Added {len(chunk_objects)} chunks to FAISS index for agent {agent_id} (total: {index.ntotal})")


# def delete_agent_index(agent_id: str):
#     """Remove the FAISS index files for an agent."""
#     idx_path = _index_path(str(agent_id))
#     ids_path = _ids_path(str(agent_id))

#     for path in [idx_path, ids_path]:
#         if os.path.exists(path):
#             os.remove(path)

#     print(f"[DELETED] FAISS index deleted for agent {agent_id}")














"""
FAISS Vector Index Manager for Knowledge Base RAG.

Uses sentence-transformers () for embeddings — runs locally, no API cost.

Handles:
- Generating embeddings via sentence-transformers
- Building / loading / saving per-agent FAISS indexes
- Adding new chunks to an existing index
"""
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import os
import numpy as np
import faiss
import time
from django.conf import settings
from sentence_transformers import SentenceTransformer
import threading


# ── Model (loaded once, reused across calls) ──────────────────
_model = None
_model_lock = threading.Lock()
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384  #  produces 384-dim vectors


def _get_model():
    global _model
    with _model_lock:
        if _model is None:
            print(f"[LOADING] Embedding model: {MODEL_NAME}...")
            # Load from local cache (no HuggingFace HTTP calls = instant)
            # Falls back to online download only if model isn't cached yet
            try:
                _model = SentenceTransformer(MODEL_NAME, local_files_only=True)
            except Exception:
                print("[DOWNLOADING] Model not cached, downloading from HuggingFace...")
                _model = SentenceTransformer(MODEL_NAME)
            print("[OK] Embedding model loaded")
    return _model


# ── Paths ─────────────────────────────────────────────────────

def _index_dir(agent_id: str) -> str:
    """Return the directory where this agent's FAISS index lives."""
    path = os.path.join(settings.MEDIA_ROOT, "faiss_indexes", str(agent_id))
    os.makedirs(path, exist_ok=True)
    return path


def _index_path(agent_id: str) -> str:
    return os.path.join(_index_dir(agent_id), "index.faiss")


def _ids_path(agent_id: str) -> str:
    return os.path.join(_index_dir(agent_id), "chunk_ids.npy")


# ── Embedding Generation ─────────────────────────────────────

def generate_embedding(text: str) -> np.ndarray:
    """Generate a single embedding vector for the given text."""
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return np.array(vector, dtype=np.float32)


def generate_embeddings_batch(texts: list) -> np.ndarray:
    """Generate embeddings for a batch of texts."""
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=len(texts) > 50)
    return np.array(vectors, dtype=np.float32)


# ── FAISS Index Management ────────────────────────────────────

def build_agent_index(agent):
    """
    Build (or rebuild) the FAISS index for an agent from all their KnowledgeChunks.
    Called by the management command and on first upload.
    """
    from knowledge.models import KnowledgeChunk

    start = time.time()
    agent_id = str(agent.id)

    chunks = list(
        KnowledgeChunk.objects.filter(
            knowledge_file__agent=agent
        ).values_list("id", "content")
    )

    if not chunks:
        print(f"[!] No chunks found for agent {agent_id}")
        return

    chunk_ids = [c[0] for c in chunks]
    chunk_texts = [c[1] for c in chunks]

    print(f"[LOADING] Generating embeddings for {len(chunk_texts)} chunks...")
    vectors = generate_embeddings_batch(chunk_texts)

    # Save embeddings back to DB
    for i, chunk_id in enumerate(chunk_ids):
        KnowledgeChunk.objects.filter(id=chunk_id).update(
            embedding=vectors[i].tobytes()
        )

    # Build FAISS index
    index = faiss.IndexFlatIP(EMBEDDING_DIM)  # Inner product = cosine on normalized vectors
    index.add(vectors)

    # Save index + chunk ID mapping
    faiss.write_index(index, _index_path(agent_id))
    np.save(_ids_path(agent_id), np.array(chunk_ids))

    # Populate cache
    global _index_cache
    with _cache_lock:
        _index_cache[agent_id] = (index, np.array(chunk_ids))

    elapsed = round(time.time() - start, 2)
    print(f"[OK] FAISS index built for agent {agent_id}: {len(chunk_ids)} chunks in {elapsed}s")


# ── Cache (store indices in memory to avoid disk I/O) ──────────
_index_cache = {}  # {agent_id: (index, chunk_ids)}
_cache_lock = threading.Lock()


def load_agent_index(agent_id: str):
    """
    Load the FAISS index and chunk ID mapping for an agent.
    Returns (index, chunk_ids) from memory cache if available, else from disk.
    """
    global _index_cache
    
    # 1. Check cache first
    with _cache_lock:
        if agent_id in _index_cache:
            return _index_cache[agent_id]

    # 2. Load from disk
    idx_path = _index_path(agent_id)
    ids_path = _ids_path(agent_id)

    if not os.path.exists(idx_path) or not os.path.exists(ids_path):
        return None, None

    try:
        index = faiss.read_index(idx_path)
        chunk_ids = np.load(ids_path)
        
        # 3. Store in cache
        with _cache_lock:
            _index_cache[agent_id] = (index, chunk_ids)
            
        return index, chunk_ids
    except Exception as e:
        print(f"[ERROR] Failed to load FAISS index for agent {agent_id}: {e}")
        return None, None


def add_chunks_to_index(agent, chunk_objects):
    """
    Embed new chunks and add them to the existing FAISS index.
    If no index exists yet, build one from scratch.

    chunk_objects: list of KnowledgeChunk instances (already saved to DB).
    """
    agent_id = str(agent.id)

    if not chunk_objects:
        return

    # Generate embeddings for new chunks
    texts = [c.content for c in chunk_objects]
    vectors = generate_embeddings_batch(texts)

    # Save embeddings to DB
    for i, chunk in enumerate(chunk_objects):
        chunk.embedding = vectors[i].tobytes()
        chunk.save(update_fields=["embedding"])

    # Load or create index
    index, existing_ids = load_agent_index(agent_id)

    if index is None:
        # First upload — create new index
        index = faiss.IndexFlatIP(EMBEDDING_DIM)
        existing_ids = np.array([], dtype=np.int64)

    # Add new vectors
    index.add(vectors)

    # Append new chunk IDs
    new_ids = np.array([c.id for c in chunk_objects], dtype=np.int64)
    all_ids = np.concatenate([existing_ids, new_ids])

    # Save
    faiss.write_index(index, _index_path(agent_id))
    np.save(_ids_path(agent_id), all_ids)

    # Invalidate cache
    global _index_cache
    with _cache_lock:
        _index_cache[agent_id] = (index, all_ids)

    print(f"[OK] Added {len(chunk_objects)} chunks to FAISS index for agent {agent_id} (total: {index.ntotal})")


def delete_agent_index(agent_id: str):
    """Remove the FAISS index files for an agent."""
    idx_path = _index_path(str(agent_id))
    ids_path = _ids_path(str(agent_id))

    for path in [idx_path, ids_path]:
        if os.path.exists(path):
            os.remove(path)

    print(f"[DELETED] FAISS index deleted for agent {agent_id}")