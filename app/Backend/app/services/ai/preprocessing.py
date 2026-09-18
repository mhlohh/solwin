import sys
from pathlib import Path
from typing import Optional

# app/Backend/app/services/ai/preprocessing.py -> parents[4] == <repo>/app
DATA_BACKEND_DIR = Path(__file__).resolve().parents[4] / "data" / "backend"
if DATA_BACKEND_DIR.exists() and str(DATA_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_BACKEND_DIR))

try:
    from clean_data import build_complaint_text, normalize_text
except ImportError:
    try:
        from app.data.backend.clean_data import build_complaint_text, normalize_text
    except ImportError:
        import re
        import unicodedata

        def normalize_text(text: Optional[str]) -> str:
            if not text:
                return ""
            normalized = unicodedata.normalize("NFKC", str(text))
            normalized = re.sub(r"[\r\n\t]+", " ", normalized)
            normalized = re.sub(r"\s+", " ", normalized)
            return normalized.strip()

        def build_complaint_text(
            message: Optional[str],
            subject: Optional[str] = None,
            max_length: int = 10_000,
        ) -> str:
            clean_subj = normalize_text(subject)
            clean_msg = normalize_text(message)
            if clean_subj and clean_msg:
                combined = f"{clean_subj} {clean_msg}"
            elif clean_subj:
                combined = clean_subj
            else:
                combined = clean_msg
            if len(combined) > max_length:
                combined = combined[:max_length].rstrip()
            return combined


def clean_text(text: str) -> str:
    """Lightweight text preprocessor using canonical data cleaning."""
    return normalize_text(text)


__all__ = ["build_complaint_text", "clean_text", "normalize_text"]
