# Debugging Services and endpoints

## How Services route traffic

A Service selects pods with `spec.selector`. Ready pods become endpoints in EndpointSlices labeled `kubernetes.io/service-name`. Traffic sent to the Service `port` is forwarded to each endpoint's `targetPort`. The `targetPort` must be a port the container actually listens on, given either as a number or as the name of a `containerPort`.

## targetPort mismatch

If `targetPort` does not match the application's listening port, pods can be Running and Ready and the Service can have ready endpoints, but connections fail with `connection refused` or time out. Compare `kubectl get service <name> -o yaml` with the pod's `containers[].ports` and with the port the process binds. Using named ports (`targetPort: http`) keeps the Service correct when the container port changes.

## No endpoints

A Service with no endpoints usually has a selector that matches no pod labels. Compare the selector with `kubectl get pods --show-labels`. If pods match but endpoints are not ready, the pods are failing readiness probes; fix the probe or the application first.

## Testing from inside the cluster

Start a temporary pod in the same namespace and call the Service DNS name, for example `curl http://<service>.<namespace>.svc.cluster.local:<port>`. Then call a pod IP on the target port directly. If the pod IP works and the Service does not, the problem is the Service definition; if both fail, the problem is the application or its listening address.
