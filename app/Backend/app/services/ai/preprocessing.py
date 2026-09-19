import re
import unicodedata


def clean_text(text: str) -> str:
    """Lightweight text preprocessor for conversation content.

    - Normalizes unicode characters
    - Normalizes whitespace (replaces tabs, multiple spaces, blank lines)
    - Removes non-printable control characters
    - Preserves URLs, email addresses, and punctuation essential for analysis
    """
    if not text:
        return ""

    # Normalize unicode to NFKC
    text = unicodedata.normalize("NFKC", text)

    # Remove non-printable control characters except newline and tab
    # \x00-\x08, \x0b, \x0c, \x0e-\x1f, \x7f-\x9f
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    # Normalize horizontal whitespace (tabs and spaces) into single spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Normalize excessive newlines (more than 2 consecutive newlines)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

    return text.strip()
