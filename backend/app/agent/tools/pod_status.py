"""Pod selection and status formatting helpers."""

from typing import Any


def label_selector(workload: dict[str, Any]) -> str:
    labels = workload.get("spec", {}).get("selector", {}).get("matchLabels", {})
    return ",".join(f"{key}={value}" for key, value in sorted(labels.items()))


def summarize_pod(pod: dict[str, Any]) -> str:
    metadata = pod.get("metadata", {})
    status = pod.get("status", {})
    lines = [f"Pod {metadata.get('name', 'unknown')}: phase={status.get('phase', 'Unknown')}"]
    for container in status.get("containerStatuses", []):
        current = container.get("state", {})
        previous = container.get("lastState", {})
        state = next(iter(current), "unknown")
        reason = current.get(state, {}).get("reason") or previous.get("terminated", {}).get("reason")
        lines.append(
            f"Container {container.get('name')}: state={state}, reason={reason or 'none'}, "
            f"restartCount={container.get('restartCount', 0)}"
        )
    return "\n".join(lines)
