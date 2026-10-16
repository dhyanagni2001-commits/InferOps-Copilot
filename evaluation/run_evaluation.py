"""Run the scenario cases against a live InferOps API and score the diagnoses."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from evaluation.metrics import average, latency_summary, score_case
from evaluation.sse import completed_result


def git_revision() -> str:
    result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    return result.stdout.strip() or "unknown"


def run(base_url: str, token: str, dataset: str) -> dict:
    with httpx.Client(timeout=120) as client:
        config = client.get(f"{base_url}/api/config").json()
        cases = [json.loads(line) for line in Path(dataset).read_text().splitlines() if line.strip()]
        cases = [case for case in cases if config["mode"] in case.get("modes", ["demo", "cluster"])]
        rows, durations = [], []
        for case in cases:
            started = time.perf_counter()
            response = client.post(f"{base_url}/api/diagnose", headers={"Authorization": f"Bearer {token}"}, json=case["request"])
            response.raise_for_status()
            result = completed_result(response.text)
            durations.append((time.perf_counter() - started) * 1000)
            scores = score_case(case["expected"], result)
            rows.append({"id": case["id"], "expected": case["expected"]["cause"], "got": result["diagnosis"]["cause"],
                         "generated_by": result["diagnosis"]["generated_by"], "latency_ms": round(durations[-1], 1),
                         "summary": result["diagnosis"]["summary"], **scores})
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git_revision": git_revision(),
        "host": platform.platform(), "backend": config, "cases": len(rows),
        "metrics": average([{key: row[key] for key in ("cause_accuracy", "keyword_recall", "citation_validity", "grounded")} for row in rows]),
        "latency": latency_summary(durations), "results": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8081")
    parser.add_argument("--token", default="dev-token")
    parser.add_argument("--dataset", default="evaluation/datasets/cases.jsonl")
    parser.add_argument("--output", default="evaluation/results/latest.json")
    parser.add_argument("--min-accuracy", type=float, default=0.0, help="exit non-zero below this cause accuracy")
    args = parser.parse_args()
    report = run(args.base_url.rstrip("/"), args.token, args.dataset)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    for row in report["results"]:
        mark = "PASS" if row["cause_accuracy"] else "FAIL"
        print(f"{mark} {row['id']:16} expected={row['expected']:24} got={row['got']:24} {row['latency_ms']:>7.1f} ms")
    print(json.dumps({key: report[key] for key in ("cases", "metrics", "latency")}, indent=2))
    if report["metrics"].get("cause_accuracy", 0) < args.min_accuracy:
        raise SystemExit(f"cause accuracy below {args.min_accuracy}")


if __name__ == "__main__":
    main()
