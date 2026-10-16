# CrashLoopBackOff

## What CrashLoopBackOff means

`CrashLoopBackOff` is not a root cause. It means a container keeps exiting and the kubelet is waiting before the next restart, with an exponential back-off capped at five minutes. The real cause is why the process exits: read `lastState.terminated.exitCode`, `reason`, and the previous container's logs.

## Reading exit codes

- Exit code 1 or another small non-zero value: the application reported an error, often missing configuration, a failed dependency connection, or an unhandled exception.
- Exit code 137: the process received SIGKILL, usually an `OOMKilled` memory limit or a liveness-probe kill.
- Exit code 139: segmentation fault.
- Exit code 143: SIGTERM, a graceful stop that may come from a failed liveness probe or a rollout.
- Exit code 0 with restarts: the main process finished; a Deployment expects long-running processes.

## Getting the logs of the crashed container

Current logs may be empty because the new container just started. Use `kubectl logs <pod> -c <container> --previous` to read the output of the last terminated container. Look for the first error, not the last line, because shutdown messages often follow the real failure.

## Common fixes

Provide required environment variables and mounted files, verify the command and arguments, make dependency connections retry instead of exiting, and confirm the image's entrypoint runs the intended process. Reproduce locally with the same image and configuration when the logs are not conclusive.
