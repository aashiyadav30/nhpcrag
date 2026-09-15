import os
import tempfile
from pathlib import Path

tmp_dir = Path(tempfile.gettempdir())
os.environ["HF_HOME"] = str(tmp_dir / "hf_home")
os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(tmp_dir / "st_home")

from backend.app import app
