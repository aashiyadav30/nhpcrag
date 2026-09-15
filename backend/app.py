"""
FastAPI Backend Application
Provides REST API endpoints for PDF uploading, document index management, and Agentic RAG chat.
"""

from typing import List, Dict, Any
from pathlib import Path
import shutil

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import UPLOAD_DIR, BASE_DIR
from backend.ingestion import extract_pages_from_pdf
from backend.chunking import chunk_extracted_pages
from backend.vector_store import add_chunks_to_store, list_indexed_documents, clear_vector_store
from backend.agent import AgenticRAGBot

app = FastAPI(title="Company Knowledge Assistant - Agentic RAG")

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Agent Instance per application session
agent_bot = AgenticRAGBot()


class ChatRequest(BaseModel):
    message: str


@app.post("/api/upload")
async def upload_pdfs(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    """
    Handles PDF file upload, text extraction, chunking, embedding generation, and vector indexing.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    processed_files = []
    total_new_chunks = 0

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            continue

        file_path = UPLOAD_DIR / file.filename
        
        try:
            # Save file to disk
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Process PDF: Ingestion -> Chunking -> Vector Storage
            extracted_pages = extract_pages_from_pdf(file_path)
            if not extracted_pages:
                file_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not extract readable text from '{file.filename}'. The file may be a scanned image or protected graphic."
                )

            chunks = chunk_extracted_pages(extracted_pages)
            chunks_added = add_chunks_to_store(chunks)
            
            total_new_chunks += chunks_added
            processed_files.append({
                "filename": file.filename,
                "total_pages": len(extracted_pages),
                "chunks_created": chunks_added
            })
        except HTTPException as http_e:
            raise http_e
        except Exception as e:
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail=f"Processing error on '{file.filename}': {str(e)}")

    indexed_docs = list_indexed_documents()

    return {
        "status": "success",
        "message": f"Successfully processed {len(processed_files)} PDF document(s).",
        "processed_files": processed_files,
        "total_documents": len(indexed_docs),
        "total_chunks": sum(doc["chunks_count"] for doc in indexed_docs)
    }


@app.get("/api/documents")
async def get_documents() -> Dict[str, Any]:
    """
    Returns list of all currently indexed PDF documents and chunk statistics.
    """
    indexed = list_indexed_documents()
    return {
        "documents": indexed,
        "count": len(indexed)
    }


@app.post("/api/chat")
async def chat(request: ChatRequest) -> Dict[str, Any]:
    """
    Processes user query using Agentic RAG decision pipeline.
    """
    user_msg = request.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    result = agent_bot.process_query(user_msg)
    return result


@app.post("/api/clear")
async def clear_session() -> Dict[str, Any]:
    """
    Clears vector store documents, uploaded PDF files, and resets chat session memory.
    """
    agent_bot.clear_history()
    clear_vector_store()
    
    # Remove files in UPLOAD_DIR
    for item in UPLOAD_DIR.glob("*"):
        if item.is_file():
            item.unlink()

    return {
        "status": "success",
        "message": "Knowledge base and conversation history cleared."
    }


# Mount Frontend static files
FRONTEND_DIR = BASE_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
