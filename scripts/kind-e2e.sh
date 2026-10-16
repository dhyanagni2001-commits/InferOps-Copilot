#!/usr/bin/env bash
# End-to-end validation on a local kind cluster:
# build images -> load into kind -> deploy -> create failure scenarios -> evaluate through the UI proxy.
set -euo pipefail
cd "$(dirname "$0")/.."
CLUSTER=${CLUSTER:-inferops}
PYTHON=${PYTHON:-.venv/bin/python}
PORT=${PORT:-18080}
OUTPUT=${OUTPUT:-evaluation/results/kind-e2e.json}

if ! kind get clusters 2>/dev/null | grep -qx "$CLUSTER"; then
  kind create cluster --name "$CLUSTER" --wait 120s
fi
kubectl config use-context "kind-$CLUSTER" >/dev/null

docker build -f deploy/docker/backend.Dockerfile -t inferops/backend:dev .
docker build -f deploy/docker/frontend.Dockerfile -t inferops/frontend:dev .
kind load docker-image inferops/backend:dev inferops/frontend:dev --name "$CLUSTER"

kubectl apply -k deploy/kubernetes/overlays/kind
# Restart so freshly loaded images with the same tag are picked up.
kubectl rollout restart deployment/inferops-backend deployment/inferops-frontend -n inferops-demo
kubectl rollout status deployment/inferops-backend -n inferops-demo --timeout=180s
kubectl rollout status deployment/inferops-frontend -n inferops-demo --timeout=180s

./scripts/run-scenario.sh all

# Exercise the full path: nginx proxy -> backend -> in-cluster kubectl with the read-only service account.
kubectl port-forward -n inferops-demo svc/inferops-frontend "$PORT:80" >/dev/null 2>&1 &
forward=$!
trap 'kill $forward 2>/dev/null || true' EXIT
for _ in $(seq 1 30); do curl -sf "http://127.0.0.1:$PORT/health/ready" >/dev/null && break; sleep 1; done

echo "Checking that the service account cannot modify or read secrets..."
for verb in "delete pods" "create deployments" "get secrets"; do
  # shellcheck disable=SC2086
  if [[ "$(kubectl auth can-i $verb -n inferops-demo --as=system:serviceaccount:inferops-demo:inferops-backend)" != no ]]; then
    echo "RBAC check failed: service account can $verb"; exit 1
  fi
done

"$PYTHON" -m evaluation.run_evaluation --base-url "http://127.0.0.1:$PORT" --token kind-local-token \
  --output "$OUTPUT" --min-accuracy 1.0
