"""
Vector Database Storage & Retrieval Module using ChromaDB.
Handles storing document embeddings and retrieving relevant chunks by cosine similarity.
"""

from typing import List, Dict, Any
import chromadb
from backend.config import CHROMA_PERSIST_DIR
from backend.embeddings import generate_embeddings, generate_single_embedding

_chroma_client = None
_collection = None
COLLECTION_NAME = "pdf_knowledge_base"


def get_vector_store():
    global _chroma_client, _collection
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


def add_chunks_to_store(chunks: List[Dict[str, Any]], batch_size: int = 64) -> int:
    """
    Adds chunked documents to the ChromaDB collection in batches with embeddings and metadata.
    Handles multi-page PDFs of any size without exceeding vector store batch limits.
    """
    if not chunks:
        return 0

    collection = get_vector_store()
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [chunk["text"] for chunk in batch]
        ids = [chunk["chunk_id"] for chunk in batch]
        metadatas = [
            {
                "filename": chunk["filename"],
                "page_number": int(chunk["page_number"]),
                "total_pages": int(chunk["total_pages"]),
                "file_path": chunk["file_path"]
            }
            for chunk in batch
        ]

        embeddings = generate_embeddings(texts)

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )

    return len(chunks)


def search_vector_store(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """
    Queries the vector database for the top_k most similar chunks.
    Returns list of dicts with text, filename, page_number, similarity_score, etc.
    """
    collection = get_vector_store()
    
    # Check if database has any documents
    if collection.count() == 0:
        return []

    query_embedding = generate_single_embedding(query)
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    retrieved_chunks = []

    if results and results.get("documents") and results["documents"][0]:
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            # ChromaDB cosine distance range is [0, 2], similarity = 1 - (distance / 2) or 1 - distance
            similarity = 1.0 - float(dist)
            retrieved_chunks.append({
                "text": doc,
                "filename": meta.get("filename", "unknown.pdf"),
                "page_number": meta.get("page_number", 1),
                "total_pages": meta.get("total_pages", 1),
                "score": round(similarity, 4)
            })

    return retrieved_chunks


def list_indexed_documents() -> List[Dict[str, Any]]:
    """
    Returns summary statistics for all indexed PDF documents.
    """
    collection = get_vector_store()
    total_chunks = collection.count()

    if total_chunks == 0:
        return []

    all_data = collection.get(include=["metadatas"])
    metadatas = all_data.get("metadatas", [])

    doc_stats = {}
    for meta in metadatas:
        filename = meta.get("filename", "Unknown")
        if filename not in doc_stats:
            doc_stats[filename] = {
                "filename": filename,
                "total_pages": meta.get("total_pages", 1),
                "chunks_count": 0
            }
        doc_stats[filename]["chunks_count"] += 1

    return list(doc_stats.values())


def clear_vector_store() -> bool:
    """
    Clears all documents from ChromaDB vector store.
    """
    global _chroma_client, _collection
    if _chroma_client is not None:
        try:
            _chroma_client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
    return True
