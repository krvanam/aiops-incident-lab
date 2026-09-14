#!/usr/bin/env bash

# A deliberately narrow training remediation tool.
# Default mode is read-only. --apply can restart only demo1/orders-api.

set -euo pipefail

NAMESPACE="demo1"
DEPLOYMENT="orders-api"
ARGOCD_NAMESPACE="argocd"
ARGOCD_APPLICATION="orders-api-gitops"
MODE="dry-run"

usage() {
  cat <<'EOF'
Usage: orders-api-guarded-remediation.sh [--apply]

Without --apply, the script only collects incident evidence.
With --apply, it performs exactly one allowed change:
  kubectl rollout restart deployment/orders-api -n demo1

It never scales, deletes, rolls back, or modifies a workload other than
demo1/orders-api.
EOF
}

if [[ $# -gt 1 ]]; then
  usage >&2
  exit 2
fi

case "${1:-}" in
  "") ;;
  --apply) MODE="apply" ;;
  -h|--help) usage; exit 0 ;;
  *)
    echo "ERROR: unsupported argument: $1" >&2
    usage >&2
    exit 2
    ;;
esac

require_resource() {
  if ! kubectl get deployment "$DEPLOYMENT" -n "$NAMESPACE" >/dev/null 2>&1; then
    echo "ERROR: expected target deployment $NAMESPACE/$DEPLOYMENT was not found." >&2
    exit 1
  fi
}

application_status() {
  kubectl get application "$ARGOCD_APPLICATION" -n "$ARGOCD_NAMESPACE" \
    -o jsonpath='{.status.sync.status}{" / "}{.status.health.status}' 2>/dev/null || true
}

print_evidence() {
  local phase="$1"

  echo
  echo "===== $phase: target deployment ====="
  kubectl get deployment "$DEPLOYMENT" -n "$NAMESPACE"

  echo
  echo "===== $phase: Orders API pods ====="
  kubectl get pods -n "$NAMESPACE" -l app=orders-api -o wide

  echo
  echo "===== $phase: recent namespace events ====="
  kubectl get events -n "$NAMESPACE" --sort-by=.metadata.creationTimestamp | tail -n 20

  echo
  echo "===== $phase: recent application logs ====="
  kubectl logs -n "$NAMESPACE" deployment/"$DEPLOYMENT" --tail=30 --prefix=true || \
    echo "WARNING: logs could not be collected from the deployment."

  echo
  echo "===== $phase: Argo CD Application ====="
  local status
  status="$(application_status)"
  if [[ -n "$status" ]]; then
    echo "$ARGOCD_APPLICATION: $status"
  else
    echo "WARNING: Argo CD Application $ARGOCD_NAMESPACE/$ARGOCD_APPLICATION was not found or has no status."
  fi
}

if ! command -v kubectl >/dev/null 2>&1; then
  echo "ERROR: kubectl is required." >&2
  exit 1
fi

require_resource

echo "Target is fixed to: $NAMESPACE/$DEPLOYMENT"
echo "Mode: $MODE"
print_evidence "BEFORE"

if [[ "$MODE" == "dry-run" ]]; then
  cat <<'EOF'

DRY RUN COMPLETE: no Kubernetes resource was changed.

Use --apply only after the incident owner decides that a controlled restart is
an appropriate mitigation for a transient, restart-safe failure. A restart does
not fix a bad release, an intentional synthetic failure, or a dependency outage.
EOF
  exit 0
fi

CURRENT_STATUS="$(application_status)"
if [[ "$CURRENT_STATUS" != "Synced / Healthy" ]]; then
  echo "ERROR: refusing remediation because Argo CD is not Synced / Healthy (current: ${CURRENT_STATUS:-unavailable})." >&2
  echo "Investigate GitOps drift or workload health before applying a restart." >&2
  exit 1
fi

echo
echo "APPROVED ACTION: restarting deployment/$DEPLOYMENT in namespace $NAMESPACE"
kubectl rollout restart deployment/"$DEPLOYMENT" -n "$NAMESPACE"

echo "Waiting up to 120 seconds for the rollout to complete..."
kubectl rollout status deployment/"$DEPLOYMENT" -n "$NAMESPACE" --timeout=120s

print_evidence "AFTER"

echo
echo "REMEDIATION COMPLETE: one controlled rollout restart was applied to $NAMESPACE/$DEPLOYMENT."
echo "Confirm that the original Prometheus alert resolves and complete the incident record."
