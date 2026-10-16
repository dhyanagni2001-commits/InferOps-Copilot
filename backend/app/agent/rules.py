"""Deterministic root-cause rules over normalized Kubernetes evidence.

Rules read only cluster evidence (never retrieved documentation), and each finding
cites the specific evidence records that triggered it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Optional

from app.schemas import Evidence

IMAGE_REASONS = {"ErrImagePull", "ImagePullBackOff", "InvalidImageName", "ErrImageNeverPull"}
CONFIG_REASONS = {"CreateContainerConfigError", "CreateContainerError"}
SUBSUMES_CRASH_LOOP = {"oom_killed", "liveness_probe_failure"}


@dataclass
class Finding:
    cause: str
    summary: str
    confidence: str
    evidence_ids: list[str]
    actions: list[str]
    commands: list[str] = field(default_factory=list)


@dataclass
class Facts:
    """Convenient views over the evidence a rule may need."""

    namespace: str
    workload: str
    status: Optional[Evidence] = None
    events: Optional[Evidence] = None
    logs: list[Evidence] = field(default_factory=list)
    service: Optional[Evidence] = None

    @classmethod
    def from_evidence(cls, evidence: list[Evidence], namespace: str, workload: str) -> Facts:
        facts = cls(namespace=namespace, workload=workload)
        for item in evidence:
            if item.source == "pod_status" and item.data.get("selected"):
                facts.status = item
            elif item.source == "pod_events" and not item.error:
                facts.events = item
            elif item.source == "pod_logs" and not item.error:
                facts.logs.append(item)
            elif item.source == "service_inspect":
                facts.service = item
        return facts

    @property
    def pod(self) -> dict[str, Any]:
        return self.status.data["selected"] if self.status else {}

    @property
    def containers(self) -> list[dict[str, Any]]:
        return self.pod.get("containers", [])

    @property
    def event_list(self) -> list[dict[str, Any]]:
        return self.events.data.get("events", []) if self.events else []

    def ids(self, *items: Optional[Evidence]) -> list[str]:
        return [item.id for item in items if item is not None]

    def describe(self) -> str:
        return f"kubectl describe pod {self.pod.get('name', self.workload)} -n {self.namespace}"

    def warnings(self, reason: str, contains: str = "") -> list[dict[str, Any]]:
        return [
            event for event in self.event_list
            if event["reason"] == reason and contains.lower() in event["message"].lower()
        ]


def _oom(facts: Facts) -> Optional[Finding]:
    for container in facts.containers:
        if "OOMKilled" in (container["reason"], container["last_reason"]):
            limit = container["resources"].get("limits", {}).get("memory", "unset")
            return Finding(
                "oom_killed",
                f"Container '{container['name']}' was OOMKilled: it exceeded its memory limit ({limit}) "
                f"and has restarted {container['restart_count']} time(s).",
                "high", facts.ids(facts.status),
                ["Measure the container's peak memory under the same workload.",
                 f"Raise the memory limit above the measured peak (currently {limit}) or reduce memory use, "
                 "for example a smaller model, batch size, or context length.",
                 "Watch restartCount and lastState after the change to confirm the fix."],
                [facts.describe(), f"kubectl top pod {facts.pod['name']} -n {facts.namespace} --containers"],
            )
    # Some runtimes report an OOM kill as reason=Error with exit code 137 (SIGKILL).
    if facts.warnings("Unhealthy", "liveness probe failed"):
        return None
    for container in facts.containers:
        limit = container["resources"].get("limits", {}).get("memory")
        if limit and 137 in (container["exit_code"], container["last_exit_code"]):
            return Finding(
                "oom_killed",
                f"Container '{container['name']}' was killed with SIGKILL (exit code 137) under a {limit} memory limit, "
                "which most likely means it exceeded that limit.",
                "medium", facts.ids(facts.status),
                ["Confirm with the container's lastState and node kernel logs.",
                 f"Measure peak memory and raise the {limit} limit or reduce memory use."],
                [facts.describe()],
            )
    return None


def _image_pull(facts: Facts) -> Optional[Finding]:
    for container in facts.containers:
        if container["reason"] in IMAGE_REASONS:
            # Prefer the detailed "Failed to pull image" event over the short "Error: ImagePullBackOff" ones.
            failures = facts.warnings("Failed", "failed to pull") or facts.warnings("Failed", "pull")
            detail = failures[-1]["message"] if failures else container["message"]
            hint = _pull_hint(detail)
            return Finding(
                "image_pull_error",
                f"Kubernetes cannot pull image '{container['image']}' for container '{container['name']}' "
                f"({container['reason']}). {hint}",
                "high", facts.ids(facts.status, facts.events if failures else None),
                ["Verify the image repository, name, and tag exist in the registry.",
                 "If the registry is private, attach an imagePullSecret with valid credentials.",
                 "Confirm cluster nodes can resolve and reach the registry host."],
                [facts.describe(), f"kubectl get events -n {facts.namespace} --field-selector involvedObject.name={facts.pod['name']}"],
            )
    return None


def _pull_hint(message: str) -> str:
    lowered = message.lower()
    if "no such host" in lowered or "lookup" in lowered:
        return "The registry hostname does not resolve."
    if "unauthorized" in lowered or "denied" in lowered or "authentication" in lowered:
        return "The registry rejected the credentials."
    if "not found" in lowered or "manifest unknown" in lowered:
        return "The image or tag does not exist."
    return "See the pull error in the pod events."


def _config(facts: Facts) -> Optional[Finding]:
    for container in facts.containers:
        if container["reason"] in CONFIG_REASONS:
            return Finding(
                "config_error",
                f"Container '{container['name']}' cannot be created: {container['message'] or container['reason']}.",
                "high", facts.ids(facts.status),
                ["Create the referenced ConfigMap or Secret, or fix the reference in the pod spec.",
                 "Check key names used by env valueFrom and volume items."],
                [facts.describe(), f"kubectl get configmaps,secrets -n {facts.namespace}"],
            )
    return None


def _unschedulable(facts: Facts) -> Optional[Finding]:
    unscheduled = any(
        condition.get("type") == "PodScheduled" and condition.get("status") == "False"
        for condition in facts.pod.get("conditions", [])
    )
    events = facts.warnings("FailedScheduling")
    if not (unscheduled or events):
        return None
    message = events[-1]["message"] if events else "The pod has not been scheduled."
    return Finding(
        "unschedulable",
        f"Pod {facts.pod['name']} is Pending because the scheduler cannot place it: {message}",
        "high", facts.ids(facts.status, facts.events if events else None),
        ["Compare the pod's resource requests with allocatable node capacity.",
         "Check node taints, tolerations, node selectors, and affinity rules.",
         "Add capacity or reduce requests, then confirm the pod is scheduled."],
        [facts.describe(), "kubectl describe nodes"],
    )


def _liveness(facts: Facts) -> Optional[Finding]:
    events = facts.warnings("Unhealthy", "liveness probe failed")
    if not events or not any(c["restart_count"] for c in facts.containers):
        return None
    return Finding(
        "liveness_probe_failure",
        f"The liveness probe is failing, so the kubelet keeps restarting the container: {events[-1]['message']}",
        "high", facts.ids(facts.status, facts.events),
        ["Check the liveness probe path, port, and timing against the application.",
         "Increase initialDelaySeconds or add a startupProbe if the app starts slowly."],
        [facts.describe()],
    )


def _crash_loop(facts: Facts) -> Optional[Finding]:
    for container in facts.containers:
        exit_code = container["last_exit_code"] if container["last_exit_code"] is not None else container["exit_code"]
        if container["reason"] == "CrashLoopBackOff" or (container["restart_count"] and exit_code not in (None, 0)):
            logs = next((item for item in facts.logs if item.data.get("container") == container["name"]), None)
            last_error = (logs.data.get("errors") or logs.data.get("lines") or [""])[-1] if logs else ""
            if last_error.strip():
                detail = f" Last log line: \"{last_error.strip()}\""
            else:
                detail = " The previous container's logs could not be retrieved, so the exit reason is not shown."
            return Finding(
                "crash_loop",
                f"Container '{container['name']}' keeps exiting with code {exit_code} and Kubernetes is backing off "
                f"restarts ({container['restart_count']} so far).{detail}",
                "high" if logs else "medium", facts.ids(facts.status, logs),
                ["Read the previous container logs for the startup error.",
                 "Check the container command, arguments, and required environment variables.",
                 "Run the image locally with the same configuration to reproduce."],
                [f"kubectl logs {facts.pod['name']} -n {facts.namespace} -c {container['name']} --previous", facts.describe()],
            )
    return None


def _readiness(facts: Facts) -> Optional[Finding]:
    events = facts.warnings("Unhealthy", "readiness probe failed")
    if not events or all(c["ready"] for c in facts.containers):
        return None
    return Finding(
        "readiness_probe_failure",
        f"The pod is running but not Ready because its readiness probe fails: {events[-1]['message']}. "
        "Services will not send it traffic.",
        "high", facts.ids(facts.status, facts.events),
        ["Verify the readiness probe path and port match an endpoint the app serves.",
         "Call the health endpoint from inside the namespace to confirm its response."],
        [facts.describe(), f"kubectl get endpointslices -n {facts.namespace}"],
    )


def _service_port(facts: Facts) -> Optional[Finding]:
    if not facts.service or not facts.service.data.get("mismatched_ports"):
        return None
    port = facts.service.data["mismatched_ports"][0]
    exposed = ", ".join(str(number) for _, number in facts.service.data["container_ports"])
    return Finding(
        "service_port_mismatch",
        f"Service {facts.service.data['name']} forwards port {port['port']} to targetPort {port['target_port']}, "
        f"but the selected containers expose {exposed}. Connections to the Service will be refused.",
        "high", facts.ids(facts.service),
        [f"Set the Service targetPort to the container port ({exposed}) or a named container port.",
         "Re-test the Service from a pod in the same namespace."],
        [f"kubectl get service {facts.service.data['name']} -n {facts.namespace} -o yaml"],
    )


def _service_selector(facts: Facts) -> Optional[Finding]:
    if not facts.service or facts.service.data.get("matched_pods"):
        return None
    return Finding(
        "service_no_endpoints",
        f"Service {facts.service.data['name']} selector {facts.service.data['selector']} matches no pods, so it has no endpoints.",
        "high", facts.ids(facts.service),
        ["Compare the Service selector with the pod template labels.",
         "Fix the selector or the labels so they match."],
        [f"kubectl get pods -n {facts.namespace} --show-labels"],
    )


def _no_pods(facts: Facts) -> Optional[Finding]:
    if facts.service or facts.status is not None:
        return None
    return Finding(
        "no_pods", f"No pods currently match {facts.workload}.", "medium", [],
        ["Check that the workload's replicas are above zero.", "Inspect ReplicaSet events for creation failures."],
        [f"kubectl describe deployment {facts.workload} -n {facts.namespace}"],
    )


def _healthy(facts: Facts) -> Optional[Finding]:
    if not facts.containers or not all(c["ready"] and not c["restart_count"] for c in facts.containers):
        return None
    # Pods that are Ready now often logged transient warnings (e.g. probes) while starting.
    warnings = [event for event in facts.event_list if event["type"] == "Warning"]
    note = f" {len(warnings)} earlier warning event(s), such as '{warnings[-1]['reason']}', did not persist." if warnings else ""
    return Finding(
        "healthy",
        f"No failure detected: pod {facts.pod['name']} is Ready with no container restarts.{note}",
        "medium", facts.ids(facts.status, facts.events),
        ["If users still see errors, inspect the Service and application-level metrics.",
         "Re-run the check while the problem is occurring."],
        [f"kubectl get pods -n {facts.namespace} -o wide"],
    )


RULES: list[Callable[[Facts], Optional[Finding]]] = [
    _oom, _image_pull, _config, _unschedulable, _service_port, _service_selector,
    _liveness, _crash_loop, _readiness, _no_pods, _healthy,
]


def evaluate(evidence: list[Evidence], namespace: str, workload: str) -> list[Finding]:
    """All matching findings, most specific first."""
    missing = next((item for item in evidence if item.source == "get_workload" and item.error), None)
    if missing:
        return [Finding("evidence_unavailable", f"The workload could not be inspected: {missing.error}", "low",
                        [], ["Check the workload name, kind, and namespace.", "Confirm the service account can read it."],
                        [f"kubectl get all -n {namespace}"])]
    facts = Facts.from_evidence(evidence, namespace, workload)
    findings = [finding for rule in RULES if (finding := rule(facts))]
    # Restarts caused by OOM or liveness kills are the crash loop; listing both would be redundant.
    if findings and findings[0].cause in SUBSUMES_CRASH_LOOP:
        findings = [item for item in findings if item.cause != "crash_loop"]
    if findings:
        return findings
    return [Finding(
        "unknown", "The available evidence does not identify a single root cause.", "low",
        [item.id for item in evidence if not item.error],
        ["Inspect the returned status and events.", "Collect application logs while the failure occurs."],
        [f"kubectl describe pod {facts.pod.get('name', workload)} -n {namespace}"],
    )]
