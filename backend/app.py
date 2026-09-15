"""
FastAPI Backend Application
Provides REST API endpoints for PDF uploading, document index management, session history, and Agentic RAG chat.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import shutil

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import UPLOAD_DIR, BASE_DIR
from backend.ingestion import extract_pages_from_pdf
from backend.chunking import chunk_extracted_pages
from backend.vector_store import add_chunks_to_store, list_indexed_documents, clear_vector_store, delete_document_from_store
from backend.agent import AgenticRAGBot
import backend.session_store as session_store

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
    session_id: Optional[str] = None


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Chat"


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


@app.delete("/api/documents/{filename}")
async def delete_document_endpoint(filename: str) -> Dict[str, Any]:
    """
    Deletes a specific PDF document from ChromaDB vector store and removes disk file.
    """
    # Delete from vector database
    delete_document_from_store(filename)

    # Remove file from disk
    file_path = UPLOAD_DIR / filename
    if file_path.exists():
        file_path.unlink(missing_ok=True)

    return {
        "status": "success",
        "message": f"Document '{filename}' deleted successfully."
    }



# ================= SESSION MANAGEMENT ENDPOINTS =================

@app.get("/api/sessions")
async def get_sessions() -> Dict[str, Any]:
    """
    Returns list of all saved chat sessions sorted by recent updates.
    """
    sessions = session_store.list_sessions()
    return {
        "sessions": sessions,
        "count": len(sessions)
    }


@app.post("/api/sessions")
async def create_new_session(req: Optional[CreateSessionRequest] = None) -> Dict[str, Any]:
    """
    Creates a new empty chat session.
    """
    title = req.title if req and req.title else "New Chat"
    session = session_store.create_session(title=title)
    return session


@app.get("/api/sessions/{session_id}")
async def get_session_detail(session_id: str) -> Dict[str, Any]:
    """
    Retrieves a specific chat session with its full message history.
    """
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return session


@app.delete("/api/sessions/{session_id}")
async def delete_session_endpoint(session_id: str) -> Dict[str, Any]:
    """
    Deletes a specific chat session.
    """
    success = session_store.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return {"status": "success", "message": f"Session {session_id} deleted."}


@app.post("/api/chat")
async def chat(request: ChatRequest) -> Dict[str, Any]:
    """
    Processes user query within a persistent chat session context.
    """
    user_msg = request.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Get or create session
    session_id = request.session_id
    current_session = None
    if session_id:
        current_session = session_store.get_session(session_id)
    
    if not current_session:
        current_session = session_store.create_session(title="New Chat")
        session_id = current_session["session_id"]

    # Extract conversation history formatted for AgenticRAGBot
    formatted_history = []
    for m in current_session.get("messages", []):
        formatted_history.append({"role": m["role"], "content": m["content"]})

    # Process query through Agent
    result = agent_bot.process_query(user_msg, session_history=formatted_history)

    # Save user & assistant messages to persistent session store
    updated_session = session_store.add_messages_to_session(session_id, user_msg, result)

    result["session_id"] = session_id
    result["session_title"] = updated_session.get("title", "Chat")
    return result


@app.post("/api/clear")
async def clear_session() -> Dict[str, Any]:
    """
    Clears vector store documents and uploaded PDF files.
    """
    agent_bot.clear_history()
    clear_vector_store()
    
    # Remove files in UPLOAD_DIR
    for item in UPLOAD_DIR.glob("*"):
        if item.is_file():
            item.unlink()

    return {
        "status": "success",
        "message": "Knowledge base repository cleared."
    }


# Mount Frontend static files
FRONTEND_DIR = BASE_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
