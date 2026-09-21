from ml_service.analytics.frequency import FrequencyTracker


def test_frequency_tracker_initial_state() -> None:
    tracker = FrequencyTracker()
    report = tracker.get_report()
    assert report.total_live_reports == 0
    assert report.by_category == {}
    assert report.by_cluster == {}
    assert report.data_source == "live_production_telemetry"


def test_frequency_tracker_accumulates_events() -> None:
    tracker = FrequencyTracker()
    tracker.record_event("DELIVERY_SHIPPING_PROBLEM", cluster_id=1)
    tracker.record_event("DELIVERY_SHIPPING_PROBLEM", cluster_id=1)
    tracker.record_event("REFUND_REQUEST", cluster_id=3)

    report = tracker.get_report()
    assert report.total_live_reports == 3
    assert report.by_category["DELIVERY_SHIPPING_PROBLEM"] == 2
    assert report.by_category["REFUND_REQUEST"] == 1
    assert report.by_cluster["1"] == 2
    assert report.by_cluster["3"] == 1


def test_frequency_tracker_reset() -> None:
    tracker = FrequencyTracker()
    tracker.record_event("PRODUCT_ISSUE", cluster_id=5)
    tracker.reset()
    report = tracker.get_report()
    assert report.total_live_reports == 0
    assert len(report.by_category) == 0
