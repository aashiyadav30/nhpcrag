"""
Embedding Generation Module
Generates dense vector embeddings for text chunks using local SentenceTransformers.
"""

from typing import List
from sentence_transformers import SentenceTransformer
from backend.config import EMBEDDING_MODEL_NAME

_embedding_model = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generates numerical vector embeddings for a list of text strings.
    """
    if not texts:
        return []

    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return embeddings.tolist()


def generate_single_embedding(text: str) -> List[float]:
    """
    Generates embedding vector for a single query text.
    """
    embeddings = generate_embeddings([text])
    return embeddings[0] if embeddings else []
