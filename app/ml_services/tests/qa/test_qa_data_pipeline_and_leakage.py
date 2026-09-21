from pathlib import Path
import pandas as pd
import pytest

from ml_service.preprocessing.cleaner import build_complaint_text, normalize_text


def test_normal_input() -> None:
    subject = "Payment failed"
    message = "Money was deducted but my order was not completed."
    combined = build_complaint_text(message, subject)
    assert "Payment failed" in combined
    assert "Money was deducted" in combined


def test_empty_message() -> None:
    subject = "Delivery issue"
    message = ""
    combined = build_complaint_text(message, subject)
    assert combined == "Delivery issue"


def test_missing_subject() -> None:
    message = "My parcel is delayed."
    combined = build_complaint_text(message, None)
    assert combined == "My parcel is delayed."


def test_missing_message() -> None:
    subject = "Defective product"
    combined = build_complaint_text(None, subject)
    assert combined == "Defective product"


def test_both_missing() -> None:
    combined = build_complaint_text(None, None)
    assert combined == ""


def test_very_short_text() -> None:
    text = "Help"
    norm = normalize_text(text)
    assert norm == "Help"


def test_very_long_text_truncation() -> None:
    long_msg = "Critical complaint message. " * 1000  # ~28,000 chars
    combined = build_complaint_text(long_msg, "Header", max_length=1000)
    assert len(combined) <= 1000
    assert combined.startswith("Header Critical")


def test_unicode_and_multilingual_characters() -> None:
    text = "₹500 payment failed for order 订单支付失败 and تم الدفع بنجاح"
    norm = normalize_text(text)
    assert "₹500" in norm
    assert "订单支付失败" in norm
    assert "تم الدفع بنجاح" in norm


def test_html_and_script_injection_handling() -> None:
    html_input = '<script>alert("test")</script><p>My payment failed</p>'
    norm = normalize_text(html_input)
    # Does not crash, normalizes spaces
    assert "alert" in norm
    assert "My payment failed" in norm


def test_special_characters_and_repeated_newlines() -> None:
    raw = "!!! ??? ### $$$ %%%\n\n\nPayment failed\n\n\nPlease help"
    norm = normalize_text(raw)
    assert "\n" not in norm
    assert "Payment failed Please help" in norm


def test_repeated_text_robustness() -> None:
    repeated = "payment failed " * 50
    norm = normalize_text(repeated)
    assert norm.startswith("payment failed")
    assert len(norm.split()) == 100


# SECTION 4: DATA LEAKAGE TEST
def test_dataset_splits_leakage_and_isolation() -> None:
    data_dir = Path("data/processed")
    if not (data_dir / "train.csv").exists():
        pytest.skip("Processed splits not found in data/processed")

    df_train = pd.read_csv(data_dir / "train.csv")
    df_val = pd.read_csv(data_dir / "val.csv")
    df_test = pd.read_csv(data_dir / "test.csv")

    # 1. Verify 'issue' column is absent in processed feature columns
    # or strictly excluded from clean_text/build_complaint_text inputs
    assert "complaint_text" in df_train.columns
    assert "issue" not in df_train.columns
    assert "category" in df_train.columns

    # 2. Check overlap between train, val, and test
    train_texts = set(df_train["complaint_text"].dropna().str.strip().str.lower())
    val_texts = set(df_val["complaint_text"].dropna().str.strip().str.lower())
    test_texts = set(df_test["complaint_text"].dropna().str.strip().str.lower())

    # Ensure strictly clean split isolation (zero duplicate text contamination)
    val_in_train = val_texts.intersection(train_texts)
    test_in_train = test_texts.intersection(train_texts)
    test_in_val = test_texts.intersection(val_texts)

    assert len(val_in_train) == 0, f"Found {len(val_in_train)} overlapping texts between train and val"
    assert len(test_in_train) == 0, f"Found {len(test_in_train)} overlapping texts between train and test"
    assert len(test_in_val) == 0, f"Found {len(test_in_val)} overlapping texts between val and test"



def test_issue_column_leakage_in_cleaner() -> None:
    import inspect
    from ml_service.preprocessing import cleaner

    # Ensure no cleaner function accepts an 'issue' argument
    sig_normalize = inspect.signature(cleaner.normalize_text)
    sig_build = inspect.signature(cleaner.build_complaint_text)

    assert "issue" not in sig_normalize.parameters
    assert "issue" not in sig_build.parameters
