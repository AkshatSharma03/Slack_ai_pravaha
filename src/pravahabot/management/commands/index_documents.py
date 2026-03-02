"""
Django management command to index documents into Upstash vector store.

Bypasses LlamaIndex storage layer — uses sentence-transformers + upstash-vector
client directly for reliable upserts.

Usage:
    python manage.py index_documents                  # indexes src/data/ folder
    python manage.py index_documents --path /my/docs  # indexes a custom folder

Supported file types: PDF, TXT, MD, DOCX
Run once after setup; run again to refresh when docs change.
"""
from pathlib import Path

from django.core.management.base import BaseCommand

import helpers


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
        # ── Imports (lazy to keep startup fast) ───────────────────────────
        from llama_index.core import SimpleDirectoryReader
        from sentence_transformers import SentenceTransformer
        from upstash_vector import Index, Vector

        # ── Resolve document path ──────────────────────────────────────────
        if options["path"]:
            doc_path = Path(options["path"])
        else:
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

        # ── Load embedding model ───────────────────────────────────────────
        self.stdout.write("🤖 Loading embedding model (BAAI/bge-small-en-v1.5)…")
        model = SentenceTransformer("BAAI/bge-small-en-v1.5")

        # ── Connect to Upstash ─────────────────────────────────────────────
        url = helpers.config("UPSTASH_VECTOR_REST_URL", default=None)
        token = helpers.config("UPSTASH_VECTOR_REST_TOKEN", default=None)

        if not url or not token:
            self.stderr.write(self.style.ERROR(
                "UPSTASH_VECTOR_REST_URL and UPSTASH_VECTOR_REST_TOKEN must be set"
            ))
            return

        index = Index(url=url, token=token)

        # ── Embed and upsert in batches ────────────────────────────────────
        self.stdout.write("⚡ Generating embeddings and upserting into Upstash…")

        BATCH = 50  # upsert 50 vectors at a time
        batch: list[Vector] = []
        total_upserted = 0

        for i, doc in enumerate(docs):
            text = doc.get_content()
            if not text.strip():
                continue

            embedding = model.encode(text, normalize_embeddings=True).tolist()
            source = str(doc.metadata.get("file_path", doc.metadata.get("file_name", "")))

            batch.append(Vector(
                id=f"doc_{i}",
                vector=embedding,
                metadata={
                    "text": text[:8000],   # Upstash metadata limit
                    "source": source,
                },
            ))

            if len(batch) >= BATCH:
                index.upsert(vectors=batch)
                total_upserted += len(batch)
                self.stdout.write(f"  ↑ Upserted {total_upserted}/{len(docs)} chunks…")
                batch = []

        # Flush remaining
        if batch:
            index.upsert(vectors=batch)
            total_upserted += len(batch)

        # ── Verify ────────────────────────────────────────────────────────
        info = index.info()
        self.stdout.write(self.style.SUCCESS(
            f"🎉 Done! {total_upserted} chunks upserted. "
            f"Upstash now reports {info.vector_count} total vectors."
        ))
