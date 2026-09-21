#!/usr/bin/env python3
"""Dataset Ingestion & Batch Inference Verification Pipeline.

Loads records from the dataset, passes each through the ML Service
inference orchestrator (/api/v1/analyze or local ComplaintClassifier),
evaluates performance, logs clean metrics, and reports results.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

# Add app/ml_services/src to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from ml_service.classification.classifier import ComplaintClassifier
from ml_service.clustering.clusterer import ComplaintClusterer
from ml_service.recommendation.engine import RecommendationEngine
from ml_service.resolution.detector import ResolutionDetector
from ml_service.security.email_analyzer import EmailAnalyzer
from ml_service.security.url_analyzer import URLAnalyzer
from ml_service.urgency.detector import UrgencyDetector


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reproducible dataset inference.")
    parser.add_argument(
        "--input",
        type=str,
        default="../data/unified_customer_phishing_data (1).csv",
        help="Path to input dataset CSV",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Number of records to analyze",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/inference_results.json",
        help="Path to save inference results",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input dataset not found at {input_path}")
        sys.exit(1)

    print(f"Initializing ML components from {BASE_DIR}...")
    primary_model_path = BASE_DIR / "models" / "complaint_classifier_v1.joblib"
    fg_model_path = BASE_DIR / "models" / "intent_classifier_v1.joblib"
    classifier = ComplaintClassifier(
        model_path=primary_model_path,
        fine_grained_model_path=fg_model_path,
    )

    cluster_model_path = BASE_DIR / "models" / "clusterer_v1.joblib"
    cluster_meta_path = BASE_DIR / "models" / "clusters_metadata.json"
    clusterer = ComplaintClusterer(
        model_path=cluster_model_path,
        metadata_path=cluster_meta_path,
    )

    urgency_detector = UrgencyDetector()
    resolution_detector = ResolutionDetector()
    recommendation_engine = RecommendationEngine(rules_path=BASE_DIR / "config" / "action_rules.yaml")
    url_analyzer = URLAnalyzer()
    email_analyzer = EmailAnalyzer()

    print(f"Loading dataset: {input_path}")
    df = pd.read_csv(input_path, nrows=args.limit)
    print(f"Analyzing {len(df)} records...")

    results = []
    start_time = time.perf_counter()

    for idx, row in df.iterrows():
        msg = str(row.get("message", "")) if pd.notnull(row.get("message")) else ""
        subj = str(row.get("subject", "")) if pd.notnull(row.get("subject")) else ""
        complaint_id = str(row.get("id", f"CMP-{idx:05d}"))

        text = f"{subj}\n{msg}".strip() if subj else msg.strip()
        if not text:
            continue

        # 1. Classify
        clf_res = classifier.classify(msg, subj)

        # 2. Cluster
        clu_res = clusterer.assign(msg, subj) if clusterer.is_loaded else None

        # 3. Urgency
        urg_res = urgency_detector.detect(msg, subj)

        # 4. Resolution
        res_res = resolution_detector.detect(msg, subj)

        # 5. Security
        urls = url_analyzer.analyze_text(text)
        emails = email_analyzer.analyze_text(text)

        # 6. Recommendation
        rec_res = recommendation_engine.recommend(
            category=clf_res.category,
            urgency=urg_res.urgency,
            resolution=res_res.status,
            security_risk="HIGH" if any(u.risk_level.value == "HIGH" for u in urls) else "LOW",
        )

        results.append({
            "complaint_id": complaint_id,
            "category": clf_res.category.value,
            "confidence": clf_res.confidence,
            "cluster_id": clu_res.cluster_id if clu_res else None,
            "urgency": urg_res.urgency.value,
            "resolution": res_res.status.value,
            "recommended_action": rec_res.primary_action.value,
            "urls_detected": len(urls),
            "emails_detected": len(emails),
        })

    elapsed_s = time.perf_counter() - start_time
    avg_ms = (elapsed_s / len(results) * 1000) if results else 0

    print(f"\nCompleted {len(results)} analyses in {elapsed_s:.2f}s ({avg_ms:.2f} ms/record)")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({
            "total_analyzed": len(results),
            "elapsed_seconds": round(elapsed_s, 2),
            "avg_ms_per_record": round(avg_ms, 2),
            "records": results,
        }, f, indent=2)

    print(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()
