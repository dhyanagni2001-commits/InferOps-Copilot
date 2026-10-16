# Container configuration errors

## CreateContainerConfigError

A container waits with reason `CreateContainerConfigError` when the kubelet cannot assemble its configuration. The message names the problem, for example `configmap "app-config" not found` or `secret "db-credentials" not found`, or `couldn't find key PORT in ConfigMap`. The container never starts, so there are no logs.

## Fixing missing references

Create the missing ConfigMap or Secret in the same namespace as the pod, or correct the name in `env[].valueFrom`, `envFrom`, or `volumes`. Key names are case sensitive. Mark a reference `optional: true` only when the application genuinely works without it. Pods pick up a newly created ConfigMap or Secret on the next start attempt.

## CreateContainerError

`CreateContainerError` is reported when the container runtime fails to create the container, for example when the command does not exist in the image, a volume mount path conflicts, or a security context cannot be applied. The message in the container status carries the runtime error.
