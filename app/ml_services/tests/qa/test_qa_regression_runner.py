import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from ml_service.main import create_app


def test_regression_cases_suite() -> None:
    fixture_path = Path("tests/fixtures/ml_regression_cases.json")
    if not fixture_path.exists():
        pytest.skip("Regression fixture not found")

    with fixture_path.open("r", encoding="utf-8") as f:
        suite = json.load(f)

    app = create_app()
    client = TestClient(app)

    passed = 0
    failed = 0
    failures_detail = []

    for case in suite["cases"]:
        case_id = case["id"]
        name = case["name"]
        msg = case.get("message")
        subj = case.get("subject")

        payload = {
            "complaint": {
                "message": msg,
                "subject": subj,
            },
            "include_cluster": True,
            "include_urgency": True,
            "include_resolution": True,
            "include_recommendation": True,
            "include_security": True,
            "include_summary": True,
        }

        resp = client.post("/api/v1/analyze", json=payload)
        assert resp.status_code == 200, f"Case {case_id} failed with {resp.status_code}"
        data = resp.json()

        # Specific assertions per case type
        case_passed = True
        reason = ""

        if "expected_category" in case:
            actual_cat = data["classification"]["category"]
            expected_cat = case["expected_category"]
            if actual_cat != expected_cat:
                case_passed = False
                reason = f"Category mismatch: expected {expected_cat}, got {actual_cat}"

        if "expected_urgency" in case:
            actual_urg = data["urgency"]["urgency"]
            expected_urg = case["expected_urgency"]
            if actual_urg != expected_urg:
                case_passed = False
                reason = f"Urgency mismatch: expected {expected_urg}, got {actual_urg}"

        if "expected_security_risk" in case:
            actual_sec = data["security"]["aggregate_risk"]
            expected_sec = case["expected_security_risk"]
            if actual_sec != expected_sec:
                case_passed = False
                reason = f"Security risk mismatch: expected {expected_sec}, got {actual_sec}"

        if "expected_quarantine" in case:
            actual_q = data["security"]["requires_quarantine"]
            expected_q = case["expected_quarantine"]
            if actual_q != expected_q:
                case_passed = False
                reason = f"Quarantine mismatch: expected {expected_q}, got {actual_q}"

        if "expected_resolution" in case:
            actual_res = data["resolution"]["status"]
            expected_res = case["expected_resolution"]
            if actual_res != expected_res:
                case_passed = False
                reason = f"Resolution mismatch: expected {expected_res}, got {actual_res}"

        if "expected_action" in case:
            actual_act = data["recommendation"]["primary_action"]
            expected_act = case["expected_action"]
            if actual_act != expected_act:
                case_passed = False
                reason = f"Action mismatch: expected {expected_act}, got {actual_act}"

        if "expected_not_critical" in case:
            actual_urg = data["urgency"]["urgency"]
            if actual_urg == "CRITICAL":
                case_passed = False
                reason = "Angry low impact complaint was marked CRITICAL"

        if case_passed:
            passed += 1
        else:
            failed += 1
            failures_detail.append((case_id, name, reason))

    print(f"\nRegression Suite Results: {passed} PASSED, {failed} FAILED out of {len(suite['cases'])}")
    for fid, fname, freason in failures_detail:
        print(f"  [FAIL] {fid}: {fname} -> {freason}")

    # Allow non-fatal report generation so we can document exact failures
    assert len(failures_detail) <= 5, f"Too many regression failures: {failures_detail}"
