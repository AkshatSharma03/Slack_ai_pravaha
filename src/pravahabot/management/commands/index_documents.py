"""
Django management command to index documents into the Upstash vector store.

Usage:
    python manage.py index_documents                  # indexes src/data/ folder
    python manage.py index_documents --path /my/docs  # indexes a custom folder

Run this once after setting up Upstash, and again whenever you add new documents.
Supported file types: PDF, TXT, MD, DOCX
"""
import os
from pathlib import Path

from django.core.management.base import BaseCommand

import helpers
from llama_index.core import Settings as LlamaSettings, SimpleDirectoryReader, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.upstash import UpstashVectorStore
from upstash_vector import Index


class Command(BaseCommand):
    help = "Index documents from a directory into the Upstash vector knowledge base"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default=None,
            help="Path to the documents folder (default: src/data/)",
        )

    def handle(self, *args, **options):
        # ── Resolve document path ──────────────────────────────────────────
        if options["path"]:
            doc_path = Path(options["path"])
        else:
            # Default: src/data/ relative to manage.py
            doc_path = Path(__file__).resolve().parents[4] / "data"

        if not doc_path.exists():
            self.stderr.write(self.style.ERROR(f"Path not found: {doc_path}"))
            return

        self.stdout.write(f"📂 Loading documents from: {doc_path}")

        # ── Load documents ─────────────────────────────────────────────────
        docs = SimpleDirectoryReader(
            str(doc_path),
            recursive=True,
            required_exts=[".pdf", ".txt", ".md", ".docx"],
        ).load_data()

        if not docs:
            self.stderr.write(self.style.ERROR("No documents found in that directory."))
            return

        self.stdout.write(f"✅ Loaded {len(docs)} document chunks")

        # ── Configure embeddings ───────────────────────────────────────────
        self.stdout.write("🤖 Loading embedding model (BAAI/bge-small-en-v1.5)…")
        LlamaSettings.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-en-v1.5"
        )
        LlamaSettings.llm = None

        # ── Connect to Upstash ─────────────────────────────────────────────
        url = helpers.config("UPSTASH_VECTOR_REST_URL", default=None)
        token = helpers.config("UPSTASH_VECTOR_REST_TOKEN", default=None)

        if not url or not token:
            self.stderr.write(
                self.style.ERROR(
                    "UPSTASH_VECTOR_REST_URL and UPSTASH_VECTOR_REST_TOKEN must be set in Railway env vars"
                )
            )
            return

        vector_store = UpstashVectorStore(url=url, token=token)

        # ── Index documents ────────────────────────────────────────────────
        self.stdout.write("⚡ Indexing into Upstash (this may take a few minutes)…")
        VectorStoreIndex.from_documents(
            docs,
            vector_store=vector_store,
            show_progress=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"🎉 Done! {len(docs)} chunks indexed into Upstash. "
                "Your knowledge base is ready."
            )
        )
