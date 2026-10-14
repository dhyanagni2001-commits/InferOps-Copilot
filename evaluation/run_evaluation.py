"""Run the checked-in cases against a live InferOps API."""

import argparse
import json
from pathlib import Path
import httpx
from evaluation.metrics import average, score_case


def completed_event(text: str) -> dict:
    for block in text.split("\n\n"):
        if block.startswith("event: completed"):
            data = next(line[6:] for line in block.splitlines() if line.startswith("data: "))
            return json.loads(data)
    raise ValueError("response did not contain a completed event")


def run(base_url: str, token: str, dataset: str) -> dict:
    cases = [json.loads(line) for line in Path(dataset).read_text().splitlines() if line.strip()]
    scores = []
    with httpx.Client(timeout=90) as client:
        for case in cases:
            response = client.post(f"{base_url}/api/diagnose", headers={"Authorization": f"Bearer {token}"}, json=case["request"])
            response.raise_for_status()
            scores.append(score_case(case["expected"], completed_event(response.text)))
    return {"cases": len(cases), "metrics": average(scores), "scores": scores}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8081")
    parser.add_argument("--token", default="dev-token")
    parser.add_argument("--dataset", default="evaluation/datasets/cases.jsonl")
    parser.add_argument("--output", default="evaluation/results/latest.json")
    args = parser.parse_args()
    report = run(args.base_url, args.token, args.dataset)
    Path(args.output).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
