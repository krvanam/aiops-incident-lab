# Runbook: Investigate an Orders API Trace

## Start with the trace ID

The instrumented application returns `X-Trace-Id` on traced business endpoints:

```bash
curl -s -D - -o /dev/null http://localhost:8081/api/orders?delay_ms=900 \
  | rg -i '^(HTTP|x-trace-id)'
```

Copy the trace ID, open Grafana **Explore**, select the **Tempo** datasource, and paste the ID into the trace query field.

## Interpret the trace

| Evidence | Meaning | Next action |
|---|---|---|
| One `GET /api/orders` span near 900 ms | Controlled `delay_ms` traffic caused the latency. | Stop the test traffic; no restart is needed. |
| Span status is error and application logs show `fail=true` | Controlled error traffic caused the 5xx response. | Stop the test traffic; let the alert window age out. |
| Long span without controlled query parameters | A real delay is possible, but not proven. | Compare Grafana p95, pod resources, logs, and recent Git changes. |
| No trace for a request | Instrumentation/export path may be unavailable. | Check Orders API, collector, and Tempo logs in that order. |

## Trace path troubleshooting

```bash
kubectl get pods -n tracing
kubectl logs -n tracing deploy/otel-collector --tail=100
kubectl logs -n tracing deploy/tempo --tail=100
kubectl get deployment/orders-api -n demo1
kubectl get application -n argocd orders-api-gitops
```

The trace backend is local and uses ephemeral storage. Traces disappear when the Tempo pod is replaced.
