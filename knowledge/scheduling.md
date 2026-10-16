# Pending pods and scheduling failures

## FailedScheduling events

A pod stays `Pending` with condition `PodScheduled=False` when the scheduler cannot find a node. The `FailedScheduling` event explains why, for example `0/3 nodes are available: 3 Insufficient cpu` or `1 node(s) had untolerated taint`.

## Insufficient resources

The scheduler compares pod `requests` with each node's allocatable capacity minus requests of pods already placed. Limits do not affect scheduling. Reduce requests to realistic values, remove unused pods, or add nodes. `kubectl describe nodes` shows allocatable capacity and allocated requests per node.

## GPU scheduling

GPU pods request `nvidia.com/gpu`. If no node advertises that resource, the event reports `Insufficient nvidia.com/gpu`. Install the NVIDIA device plugin or GPU Operator and confirm `kubectl get nodes -o jsonpath='{.items[*].status.allocatable}'` lists `nvidia.com/gpu`. GPU nodes are often tainted; GPU pods then need a matching toleration.

## Taints, affinity, and volumes

Pods without a matching toleration cannot run on tainted nodes. `nodeSelector` and node affinity restrict placement to labeled nodes. A PersistentVolumeClaim that is unbound, or bound to a volume in another zone, also blocks scheduling and appears in the same event.
