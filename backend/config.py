import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Detect if running in Vercel or read-only serverless environment
IS_VERCEL = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))

if IS_VERCEL:
    tmp_dir = Path(tempfile.gettempdir())
    UPLOAD_DIR = tmp_dir / "uploaded_pdfs"
    CHROMA_PERSIST_DIR = tmp_dir / "chroma_db"
    SESSIONS_DIR = tmp_dir / "chat_sessions"
    os.environ["HF_HOME"] = str(tmp_dir / "hf_home")
    os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(tmp_dir / "st_home")
else:
    UPLOAD_DIR = BASE_DIR / "uploaded_pdfs"
    CHROMA_PERSIST_DIR = BASE_DIR / "chroma_db"
    SESSIONS_DIR = BASE_DIR / "chat_sessions"

try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"Warning creating storage directories: {e}")


# API Keys & LLM Provider Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower()  # 'openai', 'gemini', or 'auto'
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

# Embedding Configuration
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

# Chunking Configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "600"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
