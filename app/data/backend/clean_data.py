import os
import re
import unicodedata
from typing import Optional
import pandas as pd


def normalize_text(text: Optional[str]) -> str:
    """Normalize whitespace, unicode characters (NFKC), and strip whitespace.

    Also removes control characters (null bytes, backspace, etc.) so that
    untrusted customer content never carries raw control sequences into the
    pipeline.
    """
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", str(text))
    # Strip control characters (includes \r, \n, \t, null bytes, backspace).
    normalized = re.sub(r"[\x00-\x1f\x7f]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def build_complaint_text(
    message: Optional[str],
    subject: Optional[str] = None,
    max_length: int = 10_000,
) -> str:
    """Safely combine subject and message without incorporating target issue."""
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


def clean_csv_data(file_path: Optional[str] = None) -> pd.DataFrame:
    """
    Cleans customer support & phishing dataset CSV.
    - Preserves dataset columns: id, domain, channel, message, subject, intent, issue, technique, phishing, sender, label.
    - Normalizes text and strips leading/trailing excessive whitespace.
    - Fills missing values (NaN) with defaults.
    - Drops duplicate records.
    """
    if not file_path:
        data_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        possible_paths = [
            os.path.join(data_dir, "unified_customer_phishing_data (1).csv"),
            os.path.join(data_dir, "unified_customer_phishing_data.csv"),
            os.path.join(data_dir, "unified_customer_phishing_data_subset.csv"),
            os.path.join(data_dir, "unified_customer_phishing_data_subset (1).csv"),
        ]
        file_path = None
        for p in possible_paths:
            if os.path.exists(p):
                file_path = p
                break

        if not file_path:
            raise FileNotFoundError(f"Data file not found in paths: {possible_paths}")

    df = pd.read_csv(file_path)

    # Standard expected columns
    all_cols = [
        "id", "domain", "channel", "message", "subject", "intent",
        "issue", "technique", "phishing", "sender", "label"
    ]
    for col in all_cols:
        if col not in df.columns:
            df[col] = ""

    # Keep all available columns or fallback to defined
    cols_to_keep = [c for c in all_cols if c in df.columns]
    df = df[cols_to_keep].copy()

    # Fill NaNs
    df["message"] = df["message"].fillna("")
    df["subject"] = df["subject"].fillna("")
    df["intent"] = df["intent"].fillna("")
    df["issue"] = df["issue"].fillna("")
    if "domain" in df.columns:
        df["domain"] = df["domain"].fillna("E-commerce/Retail")
    if "channel" in df.columns:
        df["channel"] = df["channel"].fillna("Email")
    if "phishing" in df.columns:
        df["phishing"] = df["phishing"].fillna(False)

    # Normalize string columns
    str_cols = ["message", "subject", "intent", "issue", "domain", "channel", "sender", "label"]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).map(normalize_text)

    # Deduplicate
    initial_count = len(df)
    dedup_subset = [c for c in ["message", "subject", "intent", "issue"] if c in df.columns]
    df = df.drop_duplicates(subset=dedup_subset).reset_index(drop=True)
    cleaned_count = len(df)

    print(f"Data Cleaning Completed: {initial_count} initial records -> {cleaned_count} unique records.")
    return df


if __name__ == "__main__":
    df_cleaned = clean_csv_data()
    print("Sample cleaned records:")
    print(df_cleaned.head(5))
