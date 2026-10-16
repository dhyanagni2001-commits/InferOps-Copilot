# Image pull failures

## ErrImagePull and ImagePullBackOff

When the kubelet cannot pull a container image, the container waits with reason `ErrImagePull`. After repeated failures Kubernetes increases the delay between attempts and reports `ImagePullBackOff`. The container never starts, so there are no container logs; the cause is in the pod events.

## Reading the pull error

`kubectl describe pod <pod>` lists events with reason `Failed`. Common messages:

- `manifest unknown` or `not found`: the repository or tag does not exist. Check spelling and whether the tag was pushed.
- `no such host` or `dial tcp: lookup`: the registry hostname does not resolve from the node.
- `unauthorized`, `authentication required`, or `denied`: the registry is private and the pod lacks valid credentials.
- `toomanyrequests`: the registry is rate limiting anonymous pulls.

## Fixing pull errors

Correct the image reference and prefer immutable tags or digests. For private registries create a `docker-registry` Secret and reference it with `imagePullSecrets` in the pod spec or on the service account. Confirm node egress and DNS can reach the registry. `InvalidImageName` means the reference itself is malformed.

## Large inference images

GPU inference images such as vLLM and Triton are several gigabytes. Slow pulls can look like a stuck `ContainerCreating` state. Pre-pull images onto GPU nodes or use a registry mirror close to the cluster.
