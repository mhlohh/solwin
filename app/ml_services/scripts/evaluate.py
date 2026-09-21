#!/usr/bin/env python3
"""Evaluate customer complaint classifier on holdout test set.

Computes Macro F1, Weighted F1, Precision, Recall, Accuracy, per-class F1,
and threshold abstention rates. Saves results to models/classification_metrics.json.
"""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)

from ml_service.api.schemas import BusinessCategory


def evaluate_model(
    test_csv: Path,
    model_path: Path,
    metrics_path: Path,
) -> None:
    print(f"Loading test split: {test_csv}")
    test_df = pd.read_csv(test_csv).fillna("")

    print(f"Loading model artifact: {model_path}")
    pipeline = joblib.load(model_path)

    X_test = test_df["complaint_text"].tolist()
    y_test = test_df["category"].tolist()

    # Predict class and probabilities
    y_pred = pipeline.predict(X_test)
    probabilities = pipeline.predict_proba(X_test)
    max_probs = np.max(probabilities, axis=1)

    # Core metrics
    accuracy = float(accuracy_score(y_test, y_pred))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))
    macro_precision = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
    macro_recall = float(recall_score(y_test, y_pred, average="macro", zero_division=0))

    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    # Per-class metrics
    per_class = {}
    for cat in BusinessCategory:
        cat_str = cat.value
        if cat_str in report:
            per_class[cat_str] = {
                "precision": round(report[cat_str]["precision"], 4),
                "recall": round(report[cat_str]["recall"], 4),
                "f1_score": round(report[cat_str]["f1-score"], 4),
                "support": int(report[cat_str]["support"]),
            }
        else:
            per_class[cat_str] = {
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "support": 0,
            }

    # Abstention rate analysis across thresholds
    thresholds = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80]
    abstention_analysis = {}
    for th in thresholds:
        abstained = int(np.sum(max_probs < th))
        abstention_rate = round(float(abstained / len(X_test)), 4)
        abstention_analysis[str(th)] = {
            "abstained_count": abstained,
            "total_count": len(X_test),
            "abstention_rate": abstention_rate,
        }

    results = {
        "model_name": "complaint-classifier",
        "version": "1.0.0",
        "dataset": "data/processed/test.csv",
        "total_test_samples": len(X_test),
        "overall_metrics": {
            "accuracy": round(accuracy, 4),
            "macro_f1": round(macro_f1, 4),
            "weighted_f1": round(weighted_f1, 4),
            "macro_precision": round(macro_precision, 4),
            "macro_recall": round(macro_recall, 4),
        },
        "per_class_metrics": per_class,
        "abstention_analysis": abstention_analysis,
    }

    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n================== Holdout Test Set Evaluation ==================")
    print(f"Accuracy:        {accuracy:.4f}")
    print(f"Macro F1:        {macro_f1:.4f}")
    print(f"Weighted F1:     {weighted_f1:.4f}")
    print(f"Macro Precision: {macro_precision:.4f}")
    print(f"Macro Recall:    {macro_recall:.4f}")
    print(f"\nReport saved to: {metrics_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate complaint classifier.")
    parser.add_argument("--test-csv", type=str, default="data/processed/test.csv")
    parser.add_argument("--model-path", type=str, default="models/complaint_classifier_v1.joblib")
    parser.add_argument("--metrics-path", type=str, default="models/classification_metrics.json")
    args = parser.parse_args()

    evaluate_model(
        Path(args.test_csv),
        Path(args.model_path),
        Path(args.metrics_path),
    )


if __name__ == "__main__":
    main()
