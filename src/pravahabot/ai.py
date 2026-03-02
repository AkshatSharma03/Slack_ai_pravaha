"""
RAG pipeline using free HuggingFace embeddings (no OpenAI key needed).

Embedding model : BAAI/bge-small-en-v1.5  (384-dim, ~130 MB, runs on CPU)
Vector store    : Upstash Vector
LLM             : Not used here — Claude in agent.py handles generation.
                  We use the retriever directly to get raw chunks; Claude
                  synthesises the final answer from those chunks.
"""
from functools import lru_cache

import helpers
from llama_index.core import Settings as LlamaSettings, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.upstash import UpstashVectorStore

UPSTASH_VECTOR_URL = helpers.config("UPSTASH_VECTOR_REST_URL", default=None)
UPSTASH_VECTOR_TOKEN = helpers.config("UPSTASH_VECTOR_REST_TOKEN", default=None)

# Free local embeddings — no API key, no cost
# IMPORTANT: your Upstash index must be created with 384 dimensions
LlamaSettings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
LlamaSettings.llm = None  # Claude handles all generation — no LLM needed here


@lru_cache
def get_vector_store_index():
    """Return a LlamaIndex VectorStoreIndex backed by Upstash."""
    vector_store = UpstashVectorStore(
        url=UPSTASH_VECTOR_URL,
        token=UPSTASH_VECTOR_TOKEN,
    )
    return VectorStoreIndex.from_vector_store(vector_store=vector_store)


def query(message: str, raw: bool = False):
    """
    Retrieve the top-k most relevant chunks for *message* and return their
    text.  We deliberately skip LlamaIndex's response synthesiser (which
    would use MockLLM and return nothing) and hand the raw chunks straight
    to Claude, which does the actual synthesis.
    """
    index = get_vector_store_index()
    retriever = index.as_retriever(similarity_top_k=5)
    nodes = retriever.retrieve(message)

    if not nodes:
        return None

    if raw:
        return nodes  # caller wants NodeWithScore objects

    # Format chunks so Claude can reason over them
    parts = []
    for i, node in enumerate(nodes, 1):
        score = f" (score: {node.score:.3f})" if node.score is not None else ""
        parts.append(f"[Chunk {i}{score}]\n{node.get_content()}")

    return "\n\n---\n\n".join(parts)
