#!/usr/bin/env bash
set -euo pipefail

name=${1:-}
case "$name" in
  oom-killed|image-pull-error|readiness-probe-error|service-port-mismatch) ;;
  *) echo "Usage: $0 {oom-killed|image-pull-error|readiness-probe-error|service-port-mismatch}"; exit 1 ;;
esac

# Scenarios are isolated to the demo namespace and never touch user workloads.
kubectl apply -f "scenarios/${name}.yaml"
kubectl get pods -n inferops-demo -w
