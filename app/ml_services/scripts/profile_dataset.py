#!/usr/bin/env python3
"""Dataset profiling and splitting CLI script for Phase 2.

Profiles raw customer complaints, validates target leakage, applies 11-category mapping,
and produces reproducible train/val/test splits without the leaked 'issue' column.
"""

import argparse
import json
from pathlib import Path

from ml_service.preprocessing.dataset import (
    create_reproducible_splits,
    profile_raw_dataset,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Profile raw dataset and generate reproducible splits."
    )
    parser.add_argument(
        "--input-csv",
        type=str,
        default="../data/unified_customer_phishing_data_subset (1).csv",
        help="Path to raw dataset CSV",
    )
    parser.add_argument(
        "--mapping-yaml",
        type=str,
        default="config/intent_category_mapping.yaml",
        help="Path to intent category mapping YAML",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed",
        help="Directory to store processed train/val/test splits and profile report",
    )
    parser.add_argument("--test-size", type=float, default=0.15, help="Test set fraction")
    parser.add_argument("--val-size", type=float, default=0.15, help="Validation set fraction")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for splitting")

    args = parser.parse_args()

    input_path = Path(args.input_csv)
    mapping_path = Path(args.mapping_yaml)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading and profiling: {input_path}")
    df, profile = profile_raw_dataset(input_path, mapping_path)

    profile_dict = {
        "total_rows": profile.total_rows,
        "missing_message_count": profile.missing_message_count,
        "missing_subject_count": profile.missing_subject_count,
        "exact_duplicate_rows": profile.exact_duplicate_rows,
        "duplicate_message_count": profile.duplicate_message_count,
        "distinct_intents": profile.distinct_intents,
        "distinct_categories": profile.distinct_categories,
        "avg_text_length": round(profile.avg_text_length, 2),
        "min_text_length": profile.min_text_length,
        "max_text_length": profile.max_text_length,
        "leakage_detected_in_issue": profile.leakage_detected_in_issue,
        "leakage_issue_match_count": profile.leakage_issue_match_count,
        "category_distribution": profile.category_distribution,
    }

    report_path = output_dir / "dataset_profile_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(profile_dict, f, indent=2)
    print(f"Profile report saved to: {report_path}")
    print(
        f"Summary: {profile.total_rows} rows, {profile.distinct_categories} categories, "
        f"{profile.distinct_intents} intents."
    )
    print(
        f"Leakage in 'issue': {profile.leakage_detected_in_issue} "
        f"({profile.leakage_issue_match_count} exact matches)."
    )

    # Exclude leaked 'issue' column from final splits, retaining only safe modeling columns
    columns_to_keep = ["message", "subject", "complaint_text", "intent", "category"]
    clean_df = df[columns_to_keep]

    print(
        f"Generating splits (test={args.test_size}, val={args.val_size}, seed={args.seed})..."
    )
    train_df, val_df, test_df = create_reproducible_splits(
        clean_df,
        test_size=args.test_size,
        val_size=args.val_size,
        random_state=args.seed,
    )

    train_path = output_dir / "train.csv"
    val_path = output_dir / "val.csv"
    test_path = output_dir / "test.csv"

    train_df.to_csv(train_path, index=False, encoding="utf-8")
    val_df.to_csv(val_path, index=False, encoding="utf-8")
    test_df.to_csv(test_path, index=False, encoding="utf-8")

    print("Saved splits:")
    print(f"  Train: {len(train_df)} rows -> {train_path}")
    print(f"  Val:   {len(val_df)} rows -> {val_path}")
    print(f"  Test:  {len(test_df)} rows -> {test_path}")


if __name__ == "__main__":
    main()
