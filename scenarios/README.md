# Controlled failure scenarios

Run these only in the dedicated `inferops-demo` namespace. `scenarios.yaml` lists each manifest, the workload to diagnose, and the expected root cause; evaluation, fixture capture, and tests all use it.

| Scenario | Workload | Expected cause | Mechanism |
|---|---|---|---|
| oom-killed | Deployment/oom-demo | oom_killed | Allocates memory past a 32Mi limit |
| image-pull-error | Deployment/broken-image | image_pull_error | Unresolvable registry host |
| readiness-probe-error | Deployment/broken-readiness | readiness_probe_failure | Probe path returns 404 |
| service-port-mismatch | Service/broken-service | service_port_mismatch | targetPort 9999, container listens on 80 |
| crash-loop | Deployment/crashloop-demo | crash_loop | Exits 3 with "MODEL_PATH … required" |
| unschedulable | Deployment/unschedulable-demo | unschedulable | Requests 64 CPU / 512Gi |
| missing-config | Deployment/missing-config | config_error | envFrom references a missing ConfigMap |
| healthy | Deployment/healthy-demo | healthy | Control case for false positives |

```bash
./scripts/run-scenario.sh all         # apply and wait until each reaches its failure state
.venv/bin/python scripts/capture_fixtures.py   # optional: re-record demo-mode fixtures
./scripts/cleanup-scenarios.sh
```
