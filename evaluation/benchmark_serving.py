"""Measure sequential API latency without external benchmark packages."""

import argparse
import statistics
import time
import httpx


def benchmark(url: str, token: str, count: int) -> None:
    payload = {"question": "Why is this restarting?", "namespace": "inferops-demo", "workload": {"kind": "Deployment", "name": "inference-demo"}}
    durations = []
    with httpx.Client(timeout=90) as client:
        for _ in range(count):
            started = time.perf_counter()
            response = client.post(f"{url}/api/diagnose", headers={"Authorization": f"Bearer {token}"}, json=payload)
            response.raise_for_status()
            durations.append((time.perf_counter() - started) * 1000)
    ordered = sorted(durations)
    print({"requests": count, "mean_ms": round(statistics.mean(durations), 2), "p95_ms": round(ordered[int(.95 * (count - 1))], 2)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8081")
    parser.add_argument("--token", default="dev-token")
    parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()
    benchmark(args.url, args.token, args.count)
