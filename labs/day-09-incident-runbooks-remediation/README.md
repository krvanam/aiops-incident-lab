# Day 9: Incident Runbooks and Guarded Remediation

## Goal

Practice the operational loop behind an SLO alert: collect evidence, make a reasoned decision, use a narrowly scoped remediation only when it is appropriate, and document the outcome.

```text
Prometheus alert / Grafana signal
              |
              v
Incident runbook and evidence collection
              |
              v
Human decision: no change or approved mitigation
              |
              v
Guarded remediation script (--apply required)
              |
              v
Kubernetes rollout status + Argo CD GitOps health
```

## Why this is guarded

Automation can make an outage worse when it acts on incomplete evidence. This lab therefore separates **diagnosis** from **change**:

- Default mode is read-only and gathers evidence.
- `--apply` is an explicit human approval point.
- The only permitted action is `rollout restart` for `demo1/orders-api`.
- The script refuses to act when Argo CD is not `Synced / Healthy`.
- It cannot scale, delete, roll back, or target another namespace/workload.

A rollout restart is a mitigation for some transient, restart-safe failures. It is **not** a fix for an intentional `?fail=true` request, a bad release, or a down dependency.

## Prerequisites

- Day 5 Orders API SLO alerts are installed.
- Day 8 Argo CD Application is `Synced / Healthy`.
- The local Kind cluster is reachable.

```bash
export KUBECONFIG="$HOME/.kube/aiops-lab-kind.yaml"

kubectl get application -n argocd orders-api-gitops
kubectl get deployment/orders-api -n demo1
```

## 1. Review the incident signal

Open the Day 7 Grafana dashboard or use PromQL to distinguish errors from latency:

```promql
sum by (status_code) (
  rate(demo_api_http_requests_total{namespace="demo1"}[5m])
)
```

```promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(demo_api_http_request_duration_seconds_bucket{namespace="demo1"}[5m])
  )
)
```

Read [the incident runbook](runbooks/orders-api-incident.md) before considering any mitigation.

## 2. Run read-only evidence collection

From this directory:

```bash
chmod +x scripts/orders-api-guarded-remediation.sh
./scripts/orders-api-guarded-remediation.sh
```

Expected outcome:

- Prints the target deployment, pods, events, application logs, and Argo CD status.
- Ends with `DRY RUN COMPLETE`.
- Makes no Kubernetes changes.

## 3. Apply one controlled restart

Only do this after reviewing the evidence and confirming that a restart is justified for the lab scenario:

```bash
./scripts/orders-api-guarded-remediation.sh --apply
```

The script restarts only `demo1/orders-api`, waits for rollout completion, and prints before/after evidence. It does not alter the replica count declared in Git; Argo CD should remain `Synced / Healthy`.

## 4. Verify recovery

```bash
kubectl get deployment/orders-api -n demo1
kubectl get application -n argocd orders-api-gitops
kubectl get pods -n demo1 -l app=orders-api
```

For an SLO alert, wait for the Prometheus time window and alert `for:` duration to elapse before expecting the alert to resolve. Record your work using [the incident template](templates/orders-api-incident-record.md).

## Evidence to capture

- Alert name, start time, customer impact, and SLO affected.
- Before/after deployment readiness and pod state.
- Relevant events and application log excerpts.
- Why a restart was or was not appropriate.
- Exact action, operator, and timestamp.
- Final Grafana/Prometheus state and Argo CD sync/health.

## Safety boundary

This is a local learning workflow. In production, remediation needs service ownership, change policy, audit logging, alert deduplication, rate limits, rollback criteria, and an approval mechanism appropriate to risk.
