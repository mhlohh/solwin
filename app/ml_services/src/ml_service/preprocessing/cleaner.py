"""Clean and normalize complaint text, re-exporting canonical data preprocessing from app.data."""

import sys
from pathlib import Path

# Add app/data to sys.path if not present so ml_service uses data/preprocessing
DATA_BACKEND_DIR = Path(__file__).resolve().parents[4] / "data" / "backend"
if DATA_BACKEND_DIR.exists() and str(DATA_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_BACKEND_DIR))

try:
    from clean_data import build_complaint_text, clean_csv_data, normalize_text
except ImportError:
    import re
    import unicodedata

    def normalize_text(text: str | None) -> str:
        if not text:
            return ""
        normalized = unicodedata.normalize("NFKC", str(text))
        normalized = re.sub(r"[\r\n\t]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def build_complaint_text(
        message: str | None,
        subject: str | None = None,
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

    clean_csv_data = None  # type: ignore[assignment]

__all__ = ["normalize_text", "build_complaint_text", "clean_csv_data"]
