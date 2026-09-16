"""
Embedding Generation Module
Generates dense vector embeddings for text chunks using FastEmbed (ONNX) with SentenceTransformers fallback.
Optimized for low RAM environments (< 350MB).
"""

from typing import List

_embedding_model = None
_model_type = None


def get_embedding_model():
    global _embedding_model, _model_type
    if _embedding_model is None:
        try:
            from fastembed import TextEmbedding
            _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            _model_type = "fastembed"
        except Exception:
            try:
                import torch
                torch.set_num_threads(1)
                torch.set_num_interop_threads(1)
            except Exception:
                pass
            from sentence_transformers import SentenceTransformer
            from backend.config import EMBEDDING_MODEL_NAME
            _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            _model_type = "sentence_transformers"
    return _embedding_model, _model_type


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generates numerical vector embeddings for a list of text strings.
    """
    if not texts:
        return []

    model, m_type = get_embedding_model()
    if m_type == "fastembed":
        embeddings = list(model.embed(texts))
        return [list(vec) for vec in embeddings]
    else:
        import torch
        with torch.no_grad():
            embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.tolist()


def generate_single_embedding(text: str) -> List[float]:
    """
    Generates embedding vector for a single query text.
    """
    embeddings = generate_embeddings([text])
    return embeddings[0] if embeddings else []

