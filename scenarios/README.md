# Controlled failure scenarios

Use only in the dedicated `inferops-demo` namespace.

```bash
./scripts/run-scenario.sh oom-killed
./scripts/cleanup-scenarios.sh
```

Available names are `oom-killed`, `image-pull-error`, `readiness-probe-error`, and `service-port-mismatch`. The OOM case intentionally allocates memory until Kubernetes terminates it.
