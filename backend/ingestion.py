"""
PDF Ingestion Module
Reads PDF documents and extracts text page-by-page with source metadata.
Uses PyMuPDF with per-page exception handling and pypdf fallback.
"""

from typing import List, Dict, Any
from pathlib import Path
from pypdf import PdfReader


def extract_pages_from_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Reads a PDF file of any length (1 page, 10 pages, 100+ pages) and extracts text page by page.
    """
    filename = pdf_path.name
    extracted_pages = []

    # 1. Try PyMuPDF (pymupdf) with per-page error handling
    try:
        import pymupdf
        doc = pymupdf.open(str(pdf_path))
        total_pages = len(doc)

        for page_idx in range(total_pages):
            page_number = page_idx + 1
            try:
                page = doc[page_idx]
                page_text = page.get_text("text") or ""
                cleaned_text = page_text.strip()

                if cleaned_text:
                    extracted_pages.append({
                        "filename": filename,
                        "page_number": page_number,
                        "total_pages": total_pages,
                        "text": cleaned_text,
                        "file_path": str(pdf_path)
                    })
            except Exception as page_err:
                print(f"Warning: Could not read page {page_number} of {filename}: {page_err}")

        if extracted_pages:
            return extracted_pages
    except Exception as e:
        print(f"PyMuPDF extraction failed for {filename}: {e}")

    # 2. Fallback to pypdf with per-page error handling
    try:
        reader = PdfReader(str(pdf_path))
        total_pages = len(reader.pages)

        for page_idx, page in enumerate(reader.pages):
            page_number = page_idx + 1
            try:
                page_text = page.extract_text() or ""
                cleaned_text = page_text.strip()

                if cleaned_text:
                    extracted_pages.append({
                        "filename": filename,
                        "page_number": page_number,
                        "total_pages": total_pages,
                        "text": cleaned_text,
                        "file_path": str(pdf_path)
                    })
            except Exception as page_err:
                print(f"Warning: pypdf error on page {page_number} of {filename}: {page_err}")
    except Exception as e:
        print(f"pypdf extraction failed for {filename}: {e}")

    return extracted_pages
