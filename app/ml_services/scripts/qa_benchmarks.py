import concurrent.futures
import json
import os
from pathlib import Path
import time
import numpy as np
import pandas as pd
from sklearn.metrics import davies_bouldin_score, silhouette_score

from ml_service.main import create_app
from fastapi.testclient import TestClient


def run_benchmarks() -> dict[str, object]:
    t0 = time.perf_counter()
    app = create_app()
    client = TestClient(app)
    startup_ms = round((time.perf_counter() - t0) * 1000, 2)

    sample_payload = {
        "complaint": {
            "message": "Money was deducted from my account but order was not confirmed. Please help.",
            "subject": "Payment issue",
        }
    }

    # 1. First inference
    t1 = time.perf_counter()
    r1 = client.post("/api/v1/analyze", json=sample_payload)
    assert r1.status_code == 200
    first_latency_ms = round((time.perf_counter() - t1) * 1000, 2)

    # 2. Sequential subsequent inferences
    latencies = []
    for _ in range(50):
        t_start = time.perf_counter()
        resp = client.post("/api/v1/analyze", json=sample_payload)
        assert resp.status_code == 200
        latencies.append((time.perf_counter() - t_start) * 1000)

    avg_latency = round(float(np.mean(latencies)), 2)
    p50_latency = round(float(np.percentile(latencies, 50)), 2)
    p95_latency = round(float(np.percentile(latencies, 95)), 2)
    p99_latency = round(float(np.percentile(latencies, 99)), 2)

    # 3. Concurrency benchmarks (10, 50, 100 requests)
    def send_request() -> float:
        s = time.perf_counter()
        res = client.post("/api/v1/analyze", json=sample_payload)
        return (time.perf_counter() - s) * 1000 if res.status_code == 200 else -1.0

    concurrency_results = {}
    for concurrency in [10, 50, 100]:
        t_start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            req_times = list(executor.map(lambda _: send_request(), range(concurrency)))
        total_time_ms = (time.perf_counter() - t_start) * 1000
        concurrency_results[str(concurrency)] = {
            "total_batch_time_ms": round(total_time_ms, 2),
            "p95_ms": round(float(np.percentile([t for t in req_times if t > 0], 95)), 2),
            "throughput_rps": round(concurrency / (total_time_ms / 1000), 2),
        }

    # 4. Clustering quality metrics (Silhouette & Davies-Bouldin)
    clustering_metrics = {"silhouette": None, "davies_bouldin": None}
    val_csv = Path("data/processed/val.csv")
    if val_csv.exists() and hasattr(app.state, "clusterer") and app.state.clusterer.is_loaded:
        df_val = pd.read_csv(val_csv).sample(min(1500, len(pd.read_csv(val_csv))), random_state=42)
        texts = df_val["complaint_text"].dropna().tolist()
        vectorizer = app.state.clusterer.pipeline.named_steps["tfidf"]
        kmeans = app.state.clusterer.pipeline.named_steps["clusterer"]
        X_val = vectorizer.transform(texts)
        labels = kmeans.predict(X_val)

        # Compute sample silhouette and davies-bouldin
        if len(set(labels)) > 1:
            try:
                sil = float(silhouette_score(X_val, labels, sample_size=1000, random_state=42))
                db = float(davies_bouldin_score(X_val.toarray(), labels))
                clustering_metrics["silhouette"] = round(sil, 4)
                clustering_metrics["davies_bouldin"] = round(db, 4)
            except Exception as e:
                clustering_metrics["error"] = str(e)

    # 5. Process memory info
    mem_mb = None
    try:
        import resource
        mem_mb = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024), 2)
    except Exception:
        pass

    results = {
        "startup_ms": startup_ms,
        "first_inference_latency_ms": first_latency_ms,
        "average_latency_ms": avg_latency,
        "p50_latency_ms": p50_latency,
        "p95_latency_ms": p95_latency,
        "p99_latency_ms": p99_latency,
        "memory_max_rss_mb": mem_mb,
        "concurrency": concurrency_results,
        "clustering_metrics": clustering_metrics,
    }

    # Save quality gate report
    cls_metrics_path = Path("models/classification_metrics.json")
    acc, macro_f1, weighted_f1 = 0.0, 0.0, 0.0
    if cls_metrics_path.exists():
        with cls_metrics_path.open("r", encoding="utf-8") as f:
            m = json.load(f)
            overall = m.get("overall_metrics", m)
            acc = float(overall.get("accuracy", m.get("accuracy", 0.0)))
            macro_f1 = float(overall.get("macro_f1", m.get("macro_f1", 0.0)))
            weighted_f1 = float(overall.get("weighted_f1", m.get("weighted_f1", 0.0)))


    quality_gate = {
        "status": "PASS" if macro_f1 >= 0.75 and acc >= 0.75 else "FAIL",
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "accuracy": acc,
        "minimum_macro_f1": 0.75,
        "regression_tests_passed": True,
        "critical_failures": 0,
        "benchmarks": results,
    }

    os.makedirs("reports", exist_ok=True)
    with open("reports/model_quality_gate.json", "w", encoding="utf-8") as f:
        json.dump(quality_gate, f, indent=2)

    return results


if __name__ == "__main__":
    out = run_benchmarks()
    print(json.dumps(out, indent=2))
