# Liveness, readiness, and startup probes

## Readiness probe failures

A readiness probe decides whether a pod receives Service traffic. When it fails, the container keeps running but the pod is marked not Ready and is removed from the Service's ready EndpointSlice endpoints. Events show `Warning Unhealthy: Readiness probe failed: HTTP probe failed with statuscode: 404` or a connection error. A readiness failure does not restart the container.

Typical causes are a probe `path` that the application does not serve, a probe `port` that does not match the listening port, an application that binds only to `127.0.0.1`, or a dependency check inside the health endpoint that fails.

## Liveness probe failures

A liveness probe failure makes the kubelet kill and restart the container. Events show `Liveness probe failed` followed by `Killing` and container restarts. An aggressive liveness probe on a slow-starting application creates a restart loop even though the application is healthy.

## Startup probes for slow starts

Add a `startupProbe` for applications with long initialization, such as model servers loading weights. Liveness and readiness checks are disabled until the startup probe succeeds, which prevents premature restarts. Size `failureThreshold * periodSeconds` to cover the worst-case startup time.

## Checking a probe manually

Run a temporary debug pod in the same namespace and request the probe URL against the pod IP, for example with `curl -v http://<pod-ip>:<port><path>`. Compare the response code with what the probe expects: HTTP probes succeed for status codes from 200 to 399.
