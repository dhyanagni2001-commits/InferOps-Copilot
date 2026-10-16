# OOMKilled containers

## What OOMKilled means

A container is terminated with reason `OOMKilled` and exit code 137 when its memory usage exceeds the memory limit set in `resources.limits.memory`. The Linux kernel's out-of-memory killer stops the process inside the container's cgroup. The kubelet then restarts the container according to the pod's `restartPolicy`; repeated kills produce `CrashLoopBackOff` with `lastState.terminated.reason: OOMKilled`.

A pod can also be evicted when the node itself runs low on memory. Node-pressure eviction appears as pod status reason `Evicted` with a message about the node being low on memory, which is different from a container hitting its own limit.

## How to confirm it

Run `kubectl describe pod <pod>` and read the container's `Last State`. `Reason: OOMKilled` and `Exit Code: 137` confirm a limit-triggered kill. `kubectl get pod <pod> -o jsonpath='{.status.containerStatuses[*].lastState}'` shows the same data. If metrics-server is installed, `kubectl top pod <pod> --containers` shows current usage, but it does not record the peak that triggered the kill.

## How to fix it

Measure the real peak memory of the workload under representative load, then set the limit above that peak with headroom. Set `requests.memory` close to typical usage so the scheduler places the pod on a node with enough memory. If the limit cannot grow, reduce memory use: smaller batch sizes, fewer worker processes, bounded caches, or for inference servers a smaller model, lower precision, or a shorter maximum context length.

## Inference servers and memory

Model servers load weights into host memory before moving them to the GPU, so host memory peaks during startup can exceed steady-state usage. Tokenizers, request queues, and KV-cache offload also consume host memory. Size the container memory limit for the startup peak, not only for steady state.
