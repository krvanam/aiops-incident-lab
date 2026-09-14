# Runbook: Orders API SLO Incident

## Trigger

Use this runbook for either alert:

- `OrdersApiHighErrorRate`
- `OrdersApiHighP95Latency`

## 1. Establish impact and scope

Record the alert name, start time, severity, affected service, and whether both availability and latency are affected.

```bash
kubectl get application -n argocd orders-api-gitops
kubectl get deployment,service,servicemonitor -n demo1 -l app=orders-api
kubectl get pods -n demo1 -l app=orders-api
```

## 2. Collect evidence before changing anything

```bash
./scripts/orders-api-guarded-remediation.sh
```

The default mode is read-only. Save the terminal output or copy the relevant results into the incident record.

Use these PromQL queries to validate the signal.

Five-minute error percentage:

```promql
100 * (
  sum(rate(demo_api_http_requests_total{namespace="demo1",status_code=~"5.."}[5m]))
  /
  sum(rate(demo_api_http_requests_total{namespace="demo1"}[5m]))
)
```

Five-minute p95 latency:

```promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(demo_api_http_request_duration_seconds_bucket{namespace="demo1"}[5m])
  )
)
```

## 3. Decide the response

| Evidence | Interpretation | Correct response |
|---|---|---|
| Requests use `?fail=true` | The lab deliberately asked the application to return HTTP 500. | Stop the test traffic; do **not** restart. |
| Requests use high `delay_ms` | The lab deliberately injected latency. | Stop the test traffic; do **not** restart. |
| Pods are ready; no crash/rollout evidence | A restart has no demonstrated benefit. | Investigate requests, dependencies, configuration, and recent Git changes. |
| Transient application fault is confirmed; restart is safe | A controlled restart may clear in-memory/transient state. | Obtain approval and use `--apply`. |
| Argo CD is `OutOfSync` or `Degraded` | Desired state or workload health is already uncertain. | Do not restart; resolve GitOps/workload state first. |
| Multiple services fail together | Likely shared dependency or cluster issue. | Escalate the broader incident; do not restart blindly. |

## 4. Apply only the approved action

```bash
./scripts/orders-api-guarded-remediation.sh --apply
```

The script has one hard-coded target: `demo1/orders-api`. It refuses changes when the Argo CD Application is not `Synced / Healthy`.

## 5. Verify and close

```bash
kubectl get deployment/orders-api -n demo1
kubectl get application -n argocd orders-api-gitops
```

Confirm that all desired replicas are ready. Then use Grafana and Prometheus to verify the alert condition falls below threshold. Alert resolution lags because the lab uses five-minute query windows and alert `for:` durations.

Complete the incident record with cause, impact, evidence, decision, action, and follow-up work.
