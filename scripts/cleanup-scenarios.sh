#!/usr/bin/env bash
set -euo pipefail

# Delete only the checked-in controlled failure resources.
for file in scenarios/oom-killed.yaml scenarios/image-pull-error.yaml scenarios/readiness-probe-error.yaml scenarios/service-port-mismatch.yaml; do
  kubectl delete -f "$file" --ignore-not-found
done
