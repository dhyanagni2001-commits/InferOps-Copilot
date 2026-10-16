#!/usr/bin/env bash
# Delete only the checked-in controlled failure resources.
set -euo pipefail
cd "$(dirname "$0")/.."
for file in scenarios/*.yaml; do
  [[ "$(basename "$file")" == scenarios.yaml ]] && continue
  kubectl delete -f "$file" --ignore-not-found
done
