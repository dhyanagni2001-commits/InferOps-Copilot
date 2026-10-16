#!/usr/bin/env bash
# Apply controlled failure scenarios to the inferops-demo namespace and wait until they fail as intended.
#   ./scripts/run-scenario.sh oom-killed      # one scenario
#   ./scripts/run-scenario.sh all             # every scenario in scenarios/scenarios.yaml
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON=${PYTHON:-.venv/bin/python}

names=$("$PYTHON" -c "import yaml; print(' '.join(s['name'] for s in yaml.safe_load(open('scenarios/scenarios.yaml'))['scenarios']))")
target=${1:-}
if [[ -z "$target" ]]; then echo "Usage: $0 {all|${names// /|}}"; exit 1; fi
[[ "$target" == all ]] && selected=$names || selected=$target
for name in $selected; do
  [[ " $names " == *" $name "* ]] || { echo "Unknown scenario: $name"; exit 1; }
done

# Scenarios are isolated to the demo namespace and never touch other workloads.
kubectl create namespace inferops-demo --dry-run=client -o yaml | kubectl apply -f - >/dev/null
for name in $selected; do kubectl apply -f "scenarios/${name}.yaml"; done
# shellcheck disable=SC2086
"$PYTHON" scripts/wait_for_scenarios.py $selected
kubectl get pods -n inferops-demo -l 'app notin (inferops-backend,inferops-frontend,qdrant)'
