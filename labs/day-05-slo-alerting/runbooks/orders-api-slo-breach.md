# Runbook: Orders API SLO Breach

## Alert intent

These alerts identify user-facing reliability risk rather than a low-level infrastructure symptom.

| Alert | Trigger | SLO relationship |
|---|---|---|
| `OrdersApiHighErrorRate` | 5xx error rate exceeds 5% for two minutes | Availability SLO: 99.9% successful requests |
| `OrdersApiHighP95Latency` | p95 latency exceeds 500 ms for two minutes | Latency SLO: 95% of requests below 500 ms |

The 5% threshold is deliberately easy to trigger in a local learning lab. A production threshold should be tied to error-budget burn rate, traffic volume, and business impact.

## Immediate checks

```bash
kubectl get pods -n demo1 -l app=orders-api
kubectl get deployment orders-api -n demo1
kubectl get events -n demo1 --sort-by=.metadata.creationTimestamp
kubectl logs -n demo1 deployment/orders-api --tail=100
```

## PromQL investigation

Five-minute availability percentage:

```promql
100 * (
  1 - (
    sum(rate(demo_api_http_requests_total{namespace="demo1",status_code=~"5.."}[5m]))
    /
    sum(rate(demo_api_http_requests_total{namespace="demo1"}[5m]))
  )
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

Request rate by response code:

```promql
sum by (status_code) (
  rate(demo_api_http_requests_total{namespace="demo1"}[5m])
)
```

## Triage decisions

| Evidence | Likely cause | First response |
|---|---|---|
| 5xx increases but latency is normal | Application or downstream dependency failure | Inspect application logs, recent configuration/release changes, and dependency health. |
| p95 rises but 5xx is stable | Slow downstream system, saturation, or inefficient code | Check resource usage, traffic volume, dependency latency, and slow requests. |
| Both alerts fire | Broad user-facing degradation | Prioritize mitigation, assess recent changes, and reduce load or roll back if appropriate. |
| No ready pods | Deployment or node issue | Follow Kubernetes pod/restart investigation first. |

## Resolution criteria

1. The alert resolves in Prometheus and Alertmanager.
2. Availability and latency return within their targets.
3. The cause, customer impact, mitigation, and follow-up action are recorded.
