"""
RAG Retrieval Tool Module
Exposes document search functionality to the Agent.
"""

from typing import Dict, Any, List
from backend.vector_store import search_vector_store


def search_pdf_knowledge_base(query: str, top_k: int = 8) -> Dict[str, Any]:
    """
    Retrieves relevant passages from uploaded PDF documents matching the search query.

    Args:
        query: The semantic search query string.
        top_k: Maximum number of relevant passages to retrieve (default 8).

    Returns:
        Dict containing formatted context string and structured source items.
    """
    # Fetch candidate pool of chunks from vector store
    results = search_vector_store(query=query, top_k=max(top_k, 10))

    # Filter by minimum relevance score threshold
    min_score_threshold = 0.15
    relevant_results = [r for r in results if r.get("score", 0) >= min_score_threshold]

    if not relevant_results:
        return {
            "found": False,
            "context": "No relevant document passages found.",
            "sources": [],
            "raw_results": []
        }

    # Target document filename boosting: Prioritize chunks matching filename keywords in query
    q_lower = query.lower()
    def boost_score(item):
        score = item.get("score", 0)
        fn_lower = item.get("filename", "").lower()
        fn_stem = fn_lower.rsplit(".", 1)[0]
        # Check for full filename or stem matches or word matches in query
        if fn_lower in q_lower or fn_stem in q_lower or (len(fn_stem) > 4 and fn_stem in q_lower):
            return score + 1.0
        return score

    sorted_results = sorted(relevant_results, key=boost_score, reverse=True)[:top_k]

    context_snippets = []
    sources = []

    for idx, item in enumerate(sorted_results):
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
        "raw_results": sorted_results
    }

