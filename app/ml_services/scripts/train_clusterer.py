#!/usr/bin/env python3
"""Train customer complaint clusterer with topic naming and c-TF-IDF keyword extraction.

Clusters complaint text using K-Means / HDBSCAN embeddings, identifies representative samples,
extracts top keywords per cluster, assigns human-readable names,
and records the model into config/model_registry.yaml.
"""

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import euclidean_distances
from sklearn.pipeline import Pipeline

from ml_service.api.schemas import BusinessCategory

CONVERSATIONAL_STOP_WORDS = {

    "thanks",
    "thank",
    "thanku",
    "thankyou",
    "good",
    "nice",
    "great",
    "okay",
    "ok",
    "yes",
    "no",
    "sir",
    "maam",
    "mam",
    "please",
    "plz",
    "hello",
    "hi",
    "happy",
    "bakvas",
    "shopzilla",
    "care",
    "customer",
    "executive",
    "service",
    "support",
    "experience",
    "conversation",
    "response",
    "helpful",
}

ALL_STOP_WORDS = list(ENGLISH_STOP_WORDS.union(CONVERSATIONAL_STOP_WORDS))


def extract_cluster_metadata(
    df: pd.DataFrame,
    labels: np.ndarray,
    pipeline: Pipeline,
    n_clusters: int,
    model_version: str = "1.0.0",
) -> list[dict[str, object]]:
    vectorizer: TfidfVectorizer = pipeline.named_steps["tfidf"]
    clusterer: MiniBatchKMeans = pipeline.named_steps["clusterer"]
    centroids = clusterer.cluster_centers_

    # Feature names for keyword extraction
    feature_names = np.array(vectorizer.get_feature_names_out())

    df["cluster_label"] = labels
    total_samples = len(df)
    clusters_info = []

    for c_id in range(n_clusters):
        c_df = df[df["cluster_label"] == c_id]
        c_size = len(c_df)
        if c_size == 0:
            continue

        percentage = round((c_size / total_samples) * 100.0, 2)

        # Dominant business category
        cat_counts = Counter(c_df["category"])
        dominant_cat = cat_counts.most_common(1)[0][0]
        # Validate category
        try:
            dominant_category_val = BusinessCategory(dominant_cat).value
        except ValueError:
            dominant_category_val = BusinessCategory.OTHER.value

        # Top keywords from centroid coordinates
        centroid = centroids[c_id]
        top_keyword_indices = centroid.argsort()[::-1][:12]
        top_keywords = [
            feature_names[idx] for idx in top_keyword_indices if centroid[idx] > 0.01
        ][:5]
        if not top_keywords:
            top_keywords = ["general", "complaint"]

        # Find representative examples (closest to centroid)
        c_vectors = vectorizer.transform(c_df["complaint_text"])
        dists = euclidean_distances(c_vectors, centroid.reshape(1, -1)).flatten()
        closest_indices = dists.argsort()[:5]
        rep_examples = c_df.iloc[closest_indices]["complaint_text"].tolist()
        # Deduplicate representative examples
        seen = set()
        clean_rep = []
        for ex in rep_examples:
            short = ex[:120].strip()
            if short and short not in seen:
                seen.add(short)
                clean_rep.append(short)

        # Generate human-readable topic name
        keywords_str = ", ".join(top_keywords[:2])
        topic_name = f"{dominant_category_val.replace('_', ' ').title()}: {keywords_str}"

        clusters_info.append(
            {
                "cluster_id": c_id,
                "name": topic_name,
                "size": c_size,
                "percentage": percentage,
                "dominant_category": dominant_category_val,
                "keywords": top_keywords,
                "representative_examples": clean_rep,
                "model_version": model_version,
            }
        )

    # Sort clusters by size descending
    clusters_info.sort(key=lambda x: int(str(x["size"])), reverse=True)
    return clusters_info


def train_clusterer(
    train_csv: Path,
    output_dir: Path,
    registry_path: Path,
    n_clusters: int = 15,
) -> None:
    print(f"Loading training data for clustering: {train_csv}")
    df = pd.read_csv(train_csv).fillna("")

    # Filter out empty or pure whitespace texts
    valid_mask = df["complaint_text"].str.strip().str.len() > 0
    df = df[valid_mask].reset_index(drop=True)
    X_texts = df["complaint_text"].tolist()

    print(f"Fitting MiniBatchKMeans (n_clusters={n_clusters}) on {len(X_texts)} samples with custom domain stopwords...")
    pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    max_features=20000,
                    sublinear_tf=True,
                    stop_words=ALL_STOP_WORDS,
                    strip_accents="unicode",
                    min_df=2,
                ),
            ),
            (
                "clusterer",
                MiniBatchKMeans(
                    n_clusters=n_clusters,
                    random_state=42,
                    batch_size=1024,
                    n_init=10,
                ),
            ),
        ]
    )

    labels = pipeline.fit_predict(X_texts)


    print("Extracting cluster topics, keywords, and representative examples...")
    clusters_meta = extract_cluster_metadata(df, labels, pipeline, n_clusters)

    output_dir.mkdir(parents=True, exist_ok=True)
    model_artifact = output_dir / "clusterer_v1.joblib"
    meta_artifact = output_dir / "clusters_metadata.json"

    joblib.dump(pipeline, model_artifact)
    with meta_artifact.open("w", encoding="utf-8") as f:
        json.dump({"clusters": clusters_meta, "total_clusters": len(clusters_meta)}, f, indent=2)

    print(f"Saved cluster model to: {model_artifact}")
    print(f"Saved cluster metadata to: {meta_artifact}")

    # Register in model_registry.yaml
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    existing_reg: dict[str, object] = {}
    if registry_path.exists():
        with registry_path.open("r", encoding="utf-8") as f:
            existing_reg = yaml.safe_load(f) or {}

    raw_list = existing_reg.get("models", [])
    models_list: list[dict[str, Any]] = raw_list if isinstance(raw_list, list) else []
    # Remove older clusterer if present
    models_list = [m for m in models_list if m.get("model_name") != "complaint-clusterer"]
    models_list.append(
        {
            "model_name": "complaint-clusterer",
            "version": "1.0.0",
            "training_dataset": "unified_customer_phishing_data_subset (1).csv",
            "training_date": today,
            "framework": "scikit-learn MiniBatchKMeans",
            "metrics": {
                "n_clusters": float(n_clusters),
            },
            "parameters": {
                "vectorizer": "TfidfVectorizer(1,2)",
                "algorithm": "MiniBatchKMeans",
                "n_clusters": str(n_clusters),
            },
            "status": "production",
        }
    )
    existing_reg["models"] = models_list

    with registry_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(existing_reg, f, sort_keys=False)
    print(f"Registered complaint-clusterer in: {registry_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train customer complaint clusterer.")
    parser.add_argument("--train-csv", type=str, default="data/processed/train.csv")
    parser.add_argument("--output-dir", type=str, default="models")
    parser.add_argument("--registry-path", type=str, default="config/model_registry.yaml")
    parser.add_argument("--n-clusters", type=int, default=15)
    args = parser.parse_args()

    train_clusterer(
        Path(args.train_csv),
        Path(args.output_dir),
        Path(args.registry_path),
        n_clusters=args.n_clusters,
    )


if __name__ == "__main__":
    main()
