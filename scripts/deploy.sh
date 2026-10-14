#!/usr/bin/env bash
set -euo pipefail

if ! kubectl get secret inferops-secrets -n inferops-demo >/dev/null 2>&1; then
  echo "Missing inferops-secrets. Copy secret.example.yaml, replace its token, and apply it first."
  exit 1
fi

kubectl apply -k deploy/kubernetes/base
kubectl rollout status deployment/inferops-backend -n inferops-demo --timeout=180s
kubectl rollout status deployment/inferops-frontend -n inferops-demo --timeout=180s
