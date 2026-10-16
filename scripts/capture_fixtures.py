"""Record real kubectl output for each controlled scenario as a demo-mode replay fixture.

Run after the scenarios have reached their failure state:
    .venv/bin/python scripts/capture_fixtures.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from pathlib import Path

import yaml

from app.agent.kubectl import FIXTURE_DIR, KubectlRunner, RecordingRunner
from app.agent.rules import evaluate
from app.agent.tools import ToolRunner
from app.schemas import DiagnoseRequest, Evidence, Workload


async def capture(scenario: dict, namespace: str) -> tuple[dict, str]:
    recorder = RecordingRunner(KubectlRunner())
    request = DiagnoseRequest(question="capture", namespace=namespace,
                              workload=Workload(kind=scenario["kind"], name=scenario["workload"]))
    evidence = [step async for step in ToolRunner(recorder).collect(request) if isinstance(step, Evidence)]
    cause = evaluate(evidence, namespace, scenario["workload"])[0].cause
    return {"scenario": scenario["name"], "workload": scenario["workload"], "calls": recorder.calls}, cause


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="scenarios/scenarios.yaml")
    parser.add_argument("--namespace", default="inferops-demo")
    args = parser.parse_args()
    version = json.loads(subprocess.run(["kubectl", "version", "-o", "json"], capture_output=True, text=True).stdout)
    server = version.get("serverVersion", {}).get("gitVersion", "unknown")
    for scenario in yaml.safe_load(Path(args.catalog).read_text())["scenarios"]:
        fixture, cause = asyncio.run(capture(scenario, args.namespace))
        fixture["kubernetes_version"] = server
        path = FIXTURE_DIR / f"{scenario['workload']}.json"
        path.write_text(json.dumps(fixture, indent=1) + "\n")
        marker = "ok" if cause == scenario["cause"] else f"MISMATCH expected {scenario['cause']}"
        print(f"{scenario['workload']:20} -> {cause:24} {marker}  ({path.stat().st_size // 1024} KiB)")


if __name__ == "__main__":
    main()
