"""Wait until each applied scenario shows its intended failure (or health) in the cluster."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import yaml


def kubectl_json(*args: str) -> dict:
    result = subprocess.run(["kubectl", *args, "-o", "json"], capture_output=True, text=True)
    return json.loads(result.stdout) if result.returncode == 0 else {}


def reached(scenario: dict, namespace: str) -> bool:
    app = scenario.get("app", scenario["workload"])
    pods = kubectl_json("get", "pods", "-n", namespace, "-l", f"app={app}").get("items", [])
    if not pods:
        return False
    pod = pods[0]
    status = (pod["status"].get("containerStatuses") or [{}])[0]
    waiting = status.get("state", {}).get("waiting", {}).get("reason", "")
    conditions = {item["type"]: item for item in pod["status"].get("conditions", [])}
    cause = scenario["cause"]
    if cause in {"oom_killed", "crash_loop"}:
        return status.get("restartCount", 0) >= 2
    if cause == "image_pull_error":
        return waiting in {"ErrImagePull", "ImagePullBackOff"}
    if cause == "config_error":
        return waiting == "CreateContainerConfigError"
    if cause == "unschedulable":
        return conditions.get("PodScheduled", {}).get("reason") == "Unschedulable"
    if cause == "readiness_probe_failure":
        events = kubectl_json("get", "events", "-n", namespace, "--field-selector", f"involvedObject.name={pod['metadata']['name']},reason=Unhealthy")
        return status.get("started") is True and bool(events.get("items"))
    return conditions.get("Ready", {}).get("status") == "True"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*", help="scenario names (default: all)")
    parser.add_argument("--catalog", default="scenarios/scenarios.yaml")
    parser.add_argument("--namespace", default="inferops-demo")
    parser.add_argument("--timeout", type=float, default=240)
    args = parser.parse_args()
    catalog = yaml.safe_load(Path(args.catalog).read_text())["scenarios"]
    pending = [item for item in catalog if not args.names or item["name"] in args.names]
    deadline = time.monotonic() + args.timeout
    while pending and time.monotonic() < deadline:
        for scenario in list(pending):
            if reached(scenario, args.namespace):
                print(f"ready: {scenario['name']} ({scenario['cause']})", flush=True)
                pending.remove(scenario)
        time.sleep(3)
    if pending:
        sys.exit(f"timed out waiting for: {', '.join(item['name'] for item in pending)}")


if __name__ == "__main__":
    main()
