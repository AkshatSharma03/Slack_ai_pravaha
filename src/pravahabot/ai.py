"""
RAG pipeline using free HuggingFace embeddings (no OpenAI key needed).

Embedding model : BAAI/bge-small-en-v1.5  (384-dim, ~130 MB, runs on CPU)
Vector store    : Upstash Vector
LLM             : Not used here — Claude in agent.py handles generation
"""
from functools import lru_cache

import helpers
import httpx
from llama_index.core import Settings as LlamaSettings, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.upstash import UpstashVectorStore
from upstash_vector import Index

UPSTASH_VECTOR_URL = helpers.config("UPSTASH_VECTOR_REST_URL", default=None)
UPSTASH_VECTOR_TOKEN = helpers.config("UPSTASH_VECTOR_REST_TOKEN", default=None)

# Free local embeddings — no API key, no cost
# IMPORTANT: your Upstash index must be created with 384 dimensions
LlamaSettings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
LlamaSettings.llm = None  # Claude handles all generation


@lru_cache
def get_vector_store_index():
    timeout = httpx.Timeout(600.0, connect=600.0)
    http_client = httpx.Client(timeout=timeout)

    upstash_index = Index(
        url=UPSTASH_VECTOR_URL,
        token=UPSTASH_VECTOR_TOKEN,
        retries=5,
        retry_interval=0.2,
    )
    upstash_index._client = http_client

    vector_store = UpstashVectorStore(
        url=UPSTASH_VECTOR_URL,
        token=UPSTASH_VECTOR_TOKEN,
    )
    vector_store._index = upstash_index

    return VectorStoreIndex.from_vector_store(vector_store=vector_store)


@lru_cache
def get_query_engine():
    return get_vector_store_index().as_query_engine(similarity_top_k=4)


def query(message: str, raw: bool = False):
    """Query the knowledge base and return a text response."""
    engine = get_query_engine()
    result = engine.query(message)
    return result if raw else result.response
