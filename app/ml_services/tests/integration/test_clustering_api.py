from fastapi.testclient import TestClient

from ml_service.main import create_app


def test_cluster_endpoint_single() -> None:
    client = TestClient(create_app())
    payload = {
        "subject": "Missing items",
        "message": "The parcel arrived but items were missing from the box.",
    }
    response = client.post("/api/v1/cluster", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "cluster_id" in data
    assert "cluster_name" in data
    assert "dominant_category" in data
    assert "distance" in data
    assert "keywords" in data


def test_cluster_endpoint_batch() -> None:
    client = TestClient(create_app())
    payload = {
        "complaints": [
            {"message": "Delayed courier"},
            {"message": "Refund money back please"},
        ]
    }
    response = client.post("/api/v1/cluster/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_processed"] == 2
    assert len(data["assignments"]) == 2


def test_get_clusters_list() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1/clusters")
    assert response.status_code == 200
    clusters = response.json()
    assert len(clusters) > 0
    first = clusters[0]
    assert "cluster_id" in first
    assert "name" in first
    assert "size" in first
    assert "keywords" in first


def test_frequency_analytics_endpoint() -> None:
    client = TestClient(create_app())
    # Send a classification request to record live telemetry
    client.post("/api/v1/classify", json={"message": "Parcel delay tracking"})

    response = client.get("/api/v1/analytics/frequency")
    assert response.status_code == 200
    data = response.json()
    assert data["total_live_reports"] >= 1
    assert data["data_source"] == "live_production_telemetry"
