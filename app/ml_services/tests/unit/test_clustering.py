from pathlib import Path

from ml_service.api.schemas import BusinessCategory
from ml_service.clustering.clusterer import ComplaintClusterer


def test_clusterer_not_loaded_on_missing_paths(tmp_path: Path) -> None:
    cl = ComplaintClusterer(
        model_path=tmp_path / "missing.joblib",
        metadata_path=tmp_path / "missing.json",
    )
    assert cl.is_loaded is False


def test_clusterer_assigns_and_lists_clusters() -> None:
    model_path = Path("models/clusterer_v1.joblib")
    meta_path = Path("models/clusters_metadata.json")

    if not model_path.exists() or not meta_path.exists():
        return

    cl = ComplaintClusterer(model_path=model_path, metadata_path=meta_path)
    assert cl.is_loaded is True

    clusters = cl.list_clusters()
    assert len(clusters) > 0
    for c in clusters:
        assert isinstance(c.cluster_id, int)
        assert len(c.name) > 0
        assert isinstance(c.dominant_category, BusinessCategory)
        assert len(c.keywords) > 0

    # Test assignment of a delivery text
    assignment = cl.assign(
        message="Delivery was postponed again without notification",
        subject="Courier delay",
    )
    assert isinstance(assignment.cluster_id, int)
    assert len(assignment.cluster_name) > 0
    assert assignment.distance >= 0.0


def test_clusterer_assign_batch() -> None:
    model_path = Path("models/clusterer_v1.joblib")
    meta_path = Path("models/clusters_metadata.json")

    if not model_path.exists() or not meta_path.exists():
        return

    cl = ComplaintClusterer(model_path=model_path, metadata_path=meta_path)
    inputs = [
        ("Return product", "Need refund"),
        ("Login password expired", None),
        ("Where is my package", "Tracking"),
    ]
    batch_results = cl.assign_batch(inputs)
    assert len(batch_results) == 3
    for res in batch_results:
        assert isinstance(res.cluster_id, int)
