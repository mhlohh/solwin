import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.metrics.pairwise import euclidean_distances

from ml_service.api.schemas import BusinessCategory, ClusterAssignment, ClusterMetadata
from ml_service.preprocessing.cleaner import build_complaint_text


class ComplaintClusterer:
    """Unsupervised customer complaint clusterer with topic naming and centroid assignment."""

    def __init__(
        self,
        model_path: Path | str,
        metadata_path: Path | str,
        model_name: str = "complaint-clusterer",
        model_version: str = "1.0.0",
    ) -> None:
        self.model_path = Path(model_path)
        self.metadata_path = Path(metadata_path)
        self.model_name = model_name
        self.model_version = model_version

        self.pipeline: Any = None
        self.clusters_metadata: dict[int, ClusterMetadata] = {}

        if self.model_path.exists():
            self.pipeline = joblib.load(self.model_path)

        if self.metadata_path.exists():
            with self.metadata_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("clusters", []):
                    c_id = item["cluster_id"]
                    self.clusters_metadata[c_id] = ClusterMetadata(
                        cluster_id=c_id,
                        name=item["name"],
                        size=item["size"],
                        percentage=item["percentage"],
                        dominant_category=BusinessCategory(item["dominant_category"]),
                        keywords=item["keywords"],
                        representative_examples=item["representative_examples"],
                        model_version=item.get("model_version", self.model_version),
                    )

    @property
    def is_loaded(self) -> bool:
        return self.pipeline is not None and len(self.clusters_metadata) > 0

    def list_clusters(self) -> list[ClusterMetadata]:
        return list(self.clusters_metadata.values())

    def assign(
        self,
        message: str | None,
        subject: str | None = None,
    ) -> ClusterAssignment:
        """Assign single complaint to nearest cluster centroid."""
        if not self.is_loaded:
            raise RuntimeError("Clustering model artifact or metadata is not loaded.")

        text = build_complaint_text(message, subject)
        if not text:
            # Fallback for empty text: assign to default or first cluster
            first = next(iter(self.clusters_metadata.values()))
            return ClusterAssignment(
                cluster_id=first.cluster_id,
                cluster_name=first.name,
                dominant_category=first.dominant_category,
                distance=1.0,
                keywords=first.keywords,
            )

        vectorizer = self.pipeline.named_steps["tfidf"]
        kmeans = self.pipeline.named_steps["clusterer"]

        vec = vectorizer.transform([text])
        centroids = kmeans.cluster_centers_

        dists = euclidean_distances(vec, centroids)[0]
        best_id = int(np.argmin(dists))
        best_dist = float(dists[best_id])

        meta = self.clusters_metadata.get(best_id)
        if meta:
            return ClusterAssignment(
                cluster_id=best_id,
                cluster_name=meta.name,
                dominant_category=meta.dominant_category,
                distance=round(best_dist, 4),
                keywords=meta.keywords,
            )

        return ClusterAssignment(
            cluster_id=best_id,
            cluster_name=f"Cluster {best_id}",
            dominant_category=BusinessCategory.OTHER,
            distance=round(best_dist, 4),
            keywords=[],
        )

    def assign_batch(
        self,
        complaints: list[tuple[str | None, str | None]] | list[tuple[str, str | None]],
    ) -> list[ClusterAssignment]:
        """Assign batch of complaints."""
        return [self.assign(msg, subj) for msg, subj in complaints]
