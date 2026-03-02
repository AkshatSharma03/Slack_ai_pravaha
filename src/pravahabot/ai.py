"""
RAG pipeline using free HuggingFace embeddings (no OpenAI key needed).

Embedding model : BAAI/bge-small-en-v1.5  (384-dim, ~130 MB, runs on CPU)
Vector store    : Upstash Vector  (queried directly via upstash-vector client)
LLM             : Not used here — Claude in agent.py handles generation.

We bypass LlamaIndex's query/storage layer entirely and talk directly to
Upstash, which is simpler and more reliable.
"""
from functools import lru_cache

import helpers

UPSTASH_VECTOR_URL = helpers.config("UPSTASH_VECTOR_REST_URL", default=None)
UPSTASH_VECTOR_TOKEN = helpers.config("UPSTASH_VECTOR_REST_TOKEN", default=None)


@lru_cache
def _get_model():
    """Load the embedding model once and cache it."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("BAAI/bge-small-en-v1.5")


@lru_cache
def _get_index():
    """Return a cached Upstash Index client."""
    from upstash_vector import Index
    return Index(url=UPSTASH_VECTOR_URL, token=UPSTASH_VECTOR_TOKEN)


def query(message: str, raw: bool = False):
    """
    Embed *message* and retrieve the top-5 most similar chunks from Upstash.
    Returns formatted text for Claude to synthesise an answer from, or None
    if nothing is found or credentials are missing.
    """
    if not UPSTASH_VECTOR_URL or not UPSTASH_VECTOR_TOKEN:
        return None

    model = _get_model()
    index = _get_index()

    embedding = model.encode(message, normalize_embeddings=True).tolist()
    results = index.query(vector=embedding, top_k=5, include_metadata=True)

    if not results:
        return None

    if raw:
        return results  # caller wants raw QueryResult objects

    # Format chunks so Claude can reason over them
    parts = []
    for i, result in enumerate(results, 1):
        score = f" (score: {result.score:.3f})" if result.score is not None else ""
        text = (result.metadata or {}).get("text", "")
        source = (result.metadata or {}).get("source", "")
        source_line = f"\nSource: {source}" if source else ""
        parts.append(f"[Chunk {i}{score}]{source_line}\n{text}")

    return "\n\n---\n\n".join(parts)
