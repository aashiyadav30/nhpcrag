"""
Session Store Module
Manages persistent chat session threads, message history, auto-titling, and deletion.
"""

import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.config import SESSIONS_DIR


def create_session(title: str = "New Chat") -> Dict[str, Any]:
    """
    Creates a new empty chat session with a unique UUID.
    """
    session_id = str(uuid.uuid4())
    now_str = datetime.now().isoformat()

    session_data = {
        "session_id": session_id,
        "title": title,
        "created_at": now_str,
        "updated_at": now_str,
        "messages": []
    }

    _save_to_file(session_data)
    return session_data


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a chat session by session_id.
    """
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if not session_file.exists():
        return None

    try:
        with session_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading session {session_id}: {e}")
        return None


def list_sessions() -> List[Dict[str, Any]]:
    """
    Lists all saved chat sessions sorted by last updated timestamp (most recent first).
    """
    sessions = []
    for file_path in SESSIONS_DIR.glob("*.json"):
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                sessions.append({
                    "session_id": data.get("session_id", file_path.stem),
                    "title": data.get("title", "Untitled Chat"),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "message_count": len(data.get("messages", []))
                })
        except Exception:
            continue

    # Sort descending by updated_at
    sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return sessions


def save_session(session_data: Dict[str, Any]) -> bool:
    """
    Saves session data object to disk.
    """
    session_data["updated_at"] = datetime.now().isoformat()
    return _save_to_file(session_data)


def delete_session(session_id: str) -> bool:
    """
    Deletes a session file from disk.
    """
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if session_file.exists():
        session_file.unlink()
        return True
    return False


def add_messages_to_session(session_id: str, user_msg: str, assistant_res: Dict[str, Any]) -> Dict[str, Any]:
    """
    Appends a user message and assistant response to a session, updating title if it is the first prompt.
    """
    session = get_session(session_id)
    if not session:
        session = create_session()
        session_id = session["session_id"]

    now = datetime.now().isoformat()

    # User message object
    user_obj = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": user_msg,
        "timestamp": now
    }

    # Assistant message object
    assistant_obj = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": assistant_res.get("answer", ""),
        "searched_docs": assistant_res.get("searched_docs", False),
        "search_query": assistant_res.get("search_query"),
        "sources": assistant_res.get("sources", []),
        "timestamp": now
    }

    session["messages"].append(user_obj)
    session["messages"].append(assistant_obj)

    # Auto-generate title from 1st prompt if default "New Chat"
    if session.get("title") == "New Chat" and len(session["messages"]) <= 2:
        session["title"] = _generate_title_from_prompt(user_msg)

    save_session(session)
    return session


def _generate_title_from_prompt(prompt: str) -> str:
    """
    Creates a clean title (3-6 words) from the user's initial prompt.
    """
    clean_p = prompt.strip()
    words = clean_p.split()
    if len(words) <= 5:
        return clean_p.capitalize()
    return " ".join(words[:5]).capitalize() + "..."


def _save_to_file(session_data: Dict[str, Any]) -> bool:
    session_id = session_data["session_id"]
    file_path = SESSIONS_DIR / f"{session_id}.json"
    try:
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving session file {session_id}: {e}")
        return False
