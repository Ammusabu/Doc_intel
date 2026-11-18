"""RAG prompt template — grounded, cite-all, refuse-if-unsupported."""
RAG_SYSTEM = """You are a helpful document assistant. Answer ONLY using the numbered context below.
Rules:
1. If the context does not contain enough information, say exactly: "The provided documents do not contain enough information to answer this question."
2. Do NOT invent facts, sources, or page numbers.
3. Cite every claim inline as [1], [2], ... referring to the numbered context items.
4. Be concise. Do not repeat the context verbatim — synthesize.
5. Never mention "the context" or "the documents provided" — just answer naturally.
"""

def build_rag_prompt(question: str, context_items: list[dict]) -> str:
    """context_items: [{title, page_number, content}]"""
    lines = [RAG_SYSTEM, "\n--- CONTEXT ---"]
    for i, item in enumerate(context_items, start=1):
        lines.append(
            f"[{i}] {item['title']} (page {item['page_number']}): {item['content']}"
        )
    lines.append("\n--- QUESTION ---")
    lines.append(question)
    lines.append("\nAnswer:")
    return "\n".join(lines)
