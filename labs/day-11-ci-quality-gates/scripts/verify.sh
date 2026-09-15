#!/usr/bin/env bash

# Local equivalent of the CI checks. It validates only and never deploys.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

cd "$REPO_ROOT"

python3 labs/day-11-ci-quality-gates/scripts/validate_yaml.py
python3 -m py_compile labs/day-04-application-sli-slo/app/main.py
python3 -m py_compile labs/day-10-aiops-incident-copilot/scripts/incident_copilot.py
bash -n labs/day-09-incident-runbooks-remediation/scripts/orders-api-guarded-remediation.sh

kubectl apply --dry-run=client --validate=false -f labs/day-01-kubernetes-foundations/k8s/
kubectl apply --dry-run=client --validate=false -f labs/day-04-application-sli-slo/k8s/10-orders-api.yaml

echo "All Day 11 local quality gates passed. No cluster resource was changed."
