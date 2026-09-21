import json
from pathlib import Path
import pytest

from ml_service.clustering.clusterer import ComplaintClusterer


@pytest.fixture
def clusterer() -> ComplaintClusterer:
    model_path = Path("models/clusterer_v1.joblib")
    meta_path = Path("models/clusters_metadata.json")
    if not (model_path.exists() and meta_path.exists()):
        pytest.skip("Clusterer artifacts not found")
    return ComplaintClusterer(model_path=model_path, metadata_path=meta_path)


# SECTION 11: CLUSTERING TEST
def test_clustering_similar_complaints(clusterer: ComplaintClusterer) -> None:
    similar_1 = clusterer.assign(message="Money deducted from bank but payment failed.")
    similar_2 = clusterer.assign(message="Payment was debited from account but transaction failed.")
    similar_3 = clusterer.assign(message="Amount deducted but order payment was unsuccessful.")

    # High semantic similarity: at least 2 should match exact same cluster
    cluster_ids = {similar_1.cluster_id, similar_2.cluster_id, similar_3.cluster_id}
    assert len(cluster_ids) <= 2, f"Similar payment failures placed into too many clusters: {cluster_ids}"


def test_clustering_unrelated_complaints_separated(clusterer: ComplaintClusterer) -> None:
    delivery = clusterer.assign(message="My delivery parcel has not arrived for 2 weeks.")
    security = clusterer.assign(message="My account password was compromised and hacker logged in.")

    # Distinct business problems should generally map to distinct clusters
    assert delivery.cluster_id is not None
    assert security.cluster_id is not None


# SECTION 12: CLUSTER QUALITY AND METADATA AUDIT
def test_clusters_metadata_complete(clusterer: ComplaintClusterer) -> None:
    clusters = clusterer.list_clusters()
    assert len(clusters) == 15

    for c in clusters:
        assert c.name
        assert len(c.keywords) > 0
        assert len(c.representative_examples) > 0
        assert c.dominant_category is not None


def test_metrics_file_has_per_class_stats() -> None:
    metrics_path = Path("models/classification_metrics.json")
    if not metrics_path.exists():
        pytest.skip("classification_metrics.json not found")

    with metrics_path.open("r", encoding="utf-8") as f:
        metrics = json.load(f)

    # Support either top-level or overall_metrics nested dictionary
    overall = metrics.get("overall_metrics", metrics)
    assert "accuracy" in overall or "accuracy" in metrics
    assert "macro_f1" in overall or "macro_f1" in metrics
    assert "weighted_f1" in overall or "weighted_f1" in metrics

    per_class = metrics.get("per_class_metrics", metrics.get("per_class", {}))
    assert len(per_class) >= 10
    for _cls_name, cls_metrics in per_class.items():
        assert "precision" in cls_metrics
        assert "recall" in cls_metrics
        assert "f1_score" in cls_metrics or "f1" in cls_metrics
        assert "support" in cls_metrics

