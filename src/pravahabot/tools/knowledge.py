"""RAG knowledge base queries — wraps the existing LlamaIndex + Upstash pipeline."""


def query_knowledge_base(question: str) -> str:
    """Search the internal knowledge base via vector similarity."""
    try:
        from pravahabot import ai

        result = ai.query(question, raw=False)
        if result and str(result).strip():
            return f"Knowledge base result:\n\n{result}"
        return "No relevant information found in the knowledge base for this query."
    except Exception as e:
        return f"Knowledge base unavailable: {str(e)}"
