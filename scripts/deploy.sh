#!/usr/bin/env bash
# Deploy an overlay to the current kubectl context: ./scripts/deploy.sh [kind|gpu]
set -euo pipefail
cd "$(dirname "$0")/.."
overlay=${1:-kind}

if [[ "$overlay" != kind ]] && ! kubectl get secret inferops-secrets -n inferops-demo >/dev/null 2>&1; then
  echo "Missing inferops-secrets. Create it first, for example:"
  echo "  kubectl create namespace inferops-demo"
  echo "  kubectl create secret generic inferops-secrets -n inferops-demo --from-literal=API_BEARER_TOKEN=\"\$(openssl rand -hex 24)\""
  exit 1
fi

kubectl apply -k "deploy/kubernetes/overlays/${overlay}"
kubectl rollout status deployment/inferops-backend -n inferops-demo --timeout=180s
kubectl rollout status deployment/inferops-frontend -n inferops-demo --timeout=180s
echo "Open the UI with: kubectl port-forward -n inferops-demo svc/inferops-frontend 8080:80"
