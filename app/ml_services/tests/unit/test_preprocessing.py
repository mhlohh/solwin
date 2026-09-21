from pathlib import Path

import pandas as pd

from ml_service.api.schemas import BusinessCategory
from ml_service.preprocessing.cleaner import build_complaint_text, normalize_text
from ml_service.preprocessing.dataset import (
    create_reproducible_splits,
    load_category_mapping,
    map_intent_to_category,
)


def test_normalize_text_whitespace_and_unicode() -> None:
    raw = "  Hello   \n\r\t World \u00a0 "
    assert normalize_text(raw) == "Hello World"
    assert normalize_text("") == ""
    assert normalize_text(None) == ""


def test_build_complaint_text_combines_subject_and_message() -> None:
    expected = "Delivery delay My order is late"
    assert build_complaint_text("My order is late", "Delivery delay") == expected
    assert build_complaint_text("My order is late", None) == "My order is late"
    assert build_complaint_text(None, "Subject only") == "Subject only"
    assert build_complaint_text("", "") == ""


def test_build_complaint_text_truncates_to_max_length() -> None:
    long_msg = "a" * 200
    res = build_complaint_text(long_msg, max_length=50)
    assert len(res) <= 50


def test_intent_category_mapping_file_completeness(tmp_path: Path) -> None:
    mapping_path = Path("config/intent_category_mapping.yaml")
    assert mapping_path.exists()

    mapping = load_category_mapping(mapping_path)
    # Validate mapping has 65 intents
    assert len(mapping) == 65

    # Every mapped value must be in BusinessCategory
    valid_categories = {c.value for c in BusinessCategory}
    for intent, cat in mapping.items():
        assert cat in valid_categories, f"Invalid category {cat} for intent {intent}"


def test_map_intent_to_category_fallback() -> None:
    mapping = {"Delayed": "DELIVERY_SHIPPING_PROBLEM"}
    assert map_intent_to_category("Delayed", mapping) == "DELIVERY_SHIPPING_PROBLEM"
    assert map_intent_to_category("Unknown XYZ Intent", mapping) == "OTHER"
    assert map_intent_to_category("", mapping) == "OTHER"


def test_reproducible_splits_logic() -> None:
    # Synthetic dataframe with various categories
    categories = [
        "DELIVERY_SHIPPING_PROBLEM",
        "PRODUCT_ISSUE",
        "PAYMENT_TRANSACTION_ISSUE",
        "SECURITY_CONCERN",
        "OTHER",
    ]
    rows = []
    for i in range(100):
        rows.append(
            {
                "message": f"Message {i}",
                "subject": "",
                "complaint_text": f"Message {i}",
                "intent": "Delayed",
                "category": categories[i % len(categories)],
                "issue": f"Delayed - Message {i}",
            }
        )
    df = pd.DataFrame(rows)

    train1, val1, test1 = create_reproducible_splits(
        df, test_size=0.2, val_size=0.2, random_state=42
    )
    train2, val2, test2 = create_reproducible_splits(
        df, test_size=0.2, val_size=0.2, random_state=42
    )

    # Verify reproducibility
    assert len(test1) == 20
    assert len(val1) == 20
    assert len(train1) == 60

    assert train1["complaint_text"].tolist() == train2["complaint_text"].tolist()
    assert test1["complaint_text"].tolist() == test2["complaint_text"].tolist()
    assert val1["complaint_text"].tolist() == val2["complaint_text"].tolist()

    # Verify no overlapping indices or samples between train, val, and test
    train_texts = set(train1["complaint_text"])
    val_texts = set(val1["complaint_text"])
    test_texts = set(test1["complaint_text"])

    assert len(train_texts.intersection(val_texts)) == 0
    assert len(train_texts.intersection(test_texts)) == 0
    assert len(val_texts.intersection(test_texts)) == 0
