"""
Text Chunking Module
Splits page text into meaningful semantic chunks while preserving source metadata.
Handles arbitrarily long strings, URLs, slide deck text, and diagrams without crashing.
"""

from typing import List, Dict, Any
from backend.config import CHUNK_SIZE, CHUNK_OVERLAP


def chunk_extracted_pages(
    pages: List[Dict[str, Any]],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP
) -> List[Dict[str, Any]]:
    """
    Splits extracted pages into smaller chunks with overlap.
    Preserves page_number, filename, and assigns a unique chunk_id to each chunk.
    """
    chunks = []

    for page in pages:
        text = page["text"]
        filename = page["filename"]
        page_number = page["page_number"]
        
        # Split page text recursively
        page_chunks = _recursive_text_split(text, chunk_size, chunk_overlap)
        
        for idx, chunk_text in enumerate(page_chunks):
            chunk_id = f"{filename}_p{page_number}_c{idx+1}"
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "filename": filename,
                "page_number": page_number,
                "total_pages": page["total_pages"],
                "file_path": page["file_path"]
            })

    return chunks


def _recursive_text_split(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """
    Recursively splits text by double newlines, single newlines, sentences, or spaces.
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []

    separators = ["\n\n", "\n", ". ", " "]
    return _split_with_separators(text, separators, chunk_size, chunk_overlap)


def _split_with_separators(text: str, separators: List[str], chunk_size: int, chunk_overlap: int) -> List[str]:
    chunks = []
    
    # Base case: no separators left, fallback to hard character slicing
    if not separators:
        step = max(1, chunk_size - chunk_overlap)
        for i in range(0, len(text), step):
            sub = text[i:i + chunk_size]
            if sub:
                chunks.append(sub)
        return chunks

    sep = separators[0]
    next_separators = separators[1:]

    parts = text.split(sep)
    current_chunk = []
    current_len = 0

    for part in parts:
        part_len = len(part) + (len(sep) if current_chunk else 0)
        
        if current_len + part_len > chunk_size and current_chunk:
            combined = sep.join(current_chunk)
            if len(combined) > chunk_size:
                chunks.extend(_split_with_separators(combined, next_separators, chunk_size, chunk_overlap))
            else:
                chunks.append(combined)
            
            # Keep overlap context from previous parts
            overlap_len = 0
            overlap_parts = []
            for p in reversed(current_chunk):
                if overlap_len + len(p) <= chunk_overlap:
                    overlap_parts.insert(0, p)
                    overlap_len += len(p)
                else:
                    break
            current_chunk = overlap_parts
            current_len = sum(len(p) for p in current_chunk)

        current_chunk.append(part)
        current_len += len(part)

    if current_chunk:
        combined = sep.join(current_chunk)
        if len(combined) > chunk_size:
            chunks.extend(_split_with_separators(combined, next_separators, chunk_size, chunk_overlap))
        else:
            chunks.append(combined)

    return [c.strip() for c in chunks if c.strip()]
