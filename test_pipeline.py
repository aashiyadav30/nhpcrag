"""
End-to-End Test & Verification Suite for Agentic RAG Chatbot
Tests PDF ingestion, chunking, vector indexing, retrieval, agent decisions, and citations.
"""

from pathlib import Path
from backend.ingestion import extract_pages_from_pdf
from backend.chunking import chunk_extracted_pages
from backend.vector_store import add_chunks_to_store, search_vector_store, clear_vector_store, list_indexed_documents
from backend.agent import AgenticRAGBot

BASE_DIR = Path(__file__).resolve().parent
SAMPLE_DIR = BASE_DIR / "sample_data"


def run_pipeline_test():
    print("=" * 70)
    print("STARTING AGENTIC RAG PIPELINE VERIFICATION TEST")
    print("=" * 70)

    # Step 1: Clear store
    clear_vector_store()
    print("✓ Vector database cleared.")

    # Step 2: PDF Ingestion & Chunking
    pdf_files = list(SAMPLE_DIR.glob("*.pdf"))
    assert len(pdf_files) > 0, "No sample PDFs found!"

    total_chunks = 0
    for pdf_path in pdf_files:
        print(f"\n[Ingesting] {pdf_path.name}...")
        pages = extract_pages_from_pdf(pdf_path)
        assert len(pages) > 0, f"Failed to extract pages from {pdf_path.name}"
        print(f"  Extracted {len(pages)} page(s).")

        chunks = chunk_extracted_pages(pages)
        assert len(chunks) > 0, "Failed to create chunks"
        print(f"  Created {len(chunks)} chunk(s). Sample chunk ID: {chunks[0]['chunk_id']}")

        added = add_chunks_to_store(chunks)
        total_chunks += added

    docs = list_indexed_documents()
    print(f"\n✓ Vector DB Indexed: {len(docs)} documents, {total_chunks} total chunks.")

    # Step 3: Test Vector Retrieval directly
    query = "annual leave policy"
    results = search_vector_store(query=query, top_k=2)
    assert len(results) > 0, "Vector retrieval failed for query!"
    print(f"\n[Vector Search Test] Query: '{query}'")
    print(f"  Top Match: Source: {results[0]['filename']} — Page {results[0]['page_number']} (Score: {results[0]['score']})")

    # Step 4: Test Agent Decision & Flow
    agent = AgenticRAGBot()

    print("\n" + "=" * 70)
    print("TESTING AGENT ROUTING & RESPONSES")
    print("=" * 70)

    # Test Case A: Document Query
    q1 = "What is the annual paid leave allowance?"
    print(f"\n[User]: {q1}")
    res1 = agent.process_query(q1)
    print(f"[Agent Searched Docs?]: {res1['searched_docs']}")
    print(f"[Agent Search Query]: {res1['search_query']}")
    print(f"[Agent Sources]: {[s['source_label'] for s in res1['sources']]}")
    print(f"[Agent Answer]:\n{res1['answer']}")
    assert res1['searched_docs'] == True, "Agent should search docs for leave query"
    assert len(res1['sources']) > 0, "Agent should return document sources"

    # Test Case B: Direct Math / General Query
    q2 = "What is 25 x 4?"
    print(f"\n[User]: {q2}")
    res2 = agent.process_query(q2)
    print(f"[Agent Searched Docs?]: {res2['searched_docs']}")
    print(f"[Agent Answer]:\n{res2['answer']}")
    assert res2['searched_docs'] == False, "Agent should NOT search docs for simple math"
    assert "100" in res2['answer'], "Math answer should contain 100"

    # Test Case C: Follow-up Query (Memory)
    q3 = "How many days of carry forward does it allow?"
    print(f"\n[User]: {q3}")
    res3 = agent.process_query(q3)
    print(f"[Agent Searched Docs?]: {res3['searched_docs']}")
    print(f"[Agent Search Query]: {res3['search_query']}")
    print(f"[Agent Sources]: {[s['source_label'] for s in res3['sources']]}")
    print(f"[Agent Answer]:\n{res3['answer']}")

    # Test Case D: Non-Existent Info (Strict No Hallucination)
    q4 = "What is the stock options vesting schedule?"
    print(f"\n[User]: {q4}")
    res4 = agent.process_query(q4)
    print(f"[Agent Answer]:\n{res4['answer']}")
    assert ("not find" in res4['answer'].lower() or "not contain" in res4['answer'].lower() or "missing" in res4['answer'].lower()), "Agent must state info is not found"

    print("\n" + "=" * 70)
    print("ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_pipeline_test()
