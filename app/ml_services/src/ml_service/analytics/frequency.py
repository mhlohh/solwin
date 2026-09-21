from collections import Counter
from datetime import UTC, datetime
from threading import Lock

from ml_service.api.schemas import FrequencyReport


class FrequencyTracker:
    """Thread-safe accumulator for live production complaint frequency and trends.

    Strictly separates incoming live production complaints from static training dataset counts.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._total_reports = 0
        self._category_counts: Counter[str] = Counter()
        self._cluster_counts: Counter[str] = Counter()
        self._started_at = datetime.now(UTC)

    def record_event(
        self,
        category: str,
        cluster_id: int | str | None = None,
    ) -> None:
        """Record an incoming live complaint event."""
        with self._lock:
            self._total_reports += 1
            self._category_counts[str(category)] += 1
            if cluster_id is not None:
                self._cluster_counts[str(cluster_id)] += 1

    def get_report(self) -> FrequencyReport:
        """Generate snapshot of live production frequency."""
        with self._lock:
            return FrequencyReport(
                total_live_reports=self._total_reports,
                by_category=dict(self._category_counts),
                by_cluster=dict(self._cluster_counts),
                timestamp=datetime.now(UTC),
                data_source="live_production_telemetry",
            )

    def reset(self) -> None:
        """Reset live counts (useful for testing or window boundaries)."""
        with self._lock:
            self._total_reports = 0
            self._category_counts.clear()
            self._cluster_counts.clear()
            self._started_at = datetime.now(UTC)
