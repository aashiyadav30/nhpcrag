"""
RAG Retrieval Tool Module
Exposes document search functionality to the Agent.
"""

from typing import Dict, Any, List
from backend.vector_store import search_vector_store


def search_pdf_knowledge_base(query: str, top_k: int = 4) -> Dict[str, Any]:
    """
    Retrieves relevant passages from uploaded PDF documents matching the search query.

    Args:
        query: The semantic search query string.
        top_k: Maximum number of relevant passages to retrieve (default 4).

    Returns:
        Dict containing formatted context string and structured source items.
    """
    results = search_vector_store(query=query, top_k=top_k)

    # Filter by minimum relevance score threshold (0.30)
    min_score_threshold = 0.30
    relevant_results = [r for r in results if r.get("score", 0) >= min_score_threshold]

    if not relevant_results:
        return {
            "found": False,
            "context": "No relevant document passages found.",
            "sources": [],
            "raw_results": []
        }

    context_snippets = []
    sources = []

    for idx, item in enumerate(relevant_results):
        fn = item["filename"]
        pg = item["page_number"]
        source_label = f"{fn} — Page {pg}"

        context_snippets.append(
            f"[Passage {idx+1} | Source: {source_label} | Score: {item['score']}]\n{item['text']}"
        )

        sources.append({
            "filename": fn,
            "page_number": pg,
            "source_label": source_label,
            "score": item["score"]
        })

    return {
        "found": True,
        "context": "\n\n---\n\n".join(context_snippets),
        "sources": sources,
        "raw_results": results
    }
