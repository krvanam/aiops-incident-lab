# Orders API: SLI and SLO Reference

## User journey

The user calls `GET /api/orders`. A successful response is HTTP 2xx; a simulated upstream failure returns HTTP 500. The FastAPI middleware records both outcomes and the request duration.

## Service-level indicators

### Availability SLI

The percentage of requests that do not return 5xx responses:

```promql
100 * (
  1 - (
    sum(rate(demo_api_http_requests_total{namespace="demo1",status_code=~"5.."}[5m]))
    /
    sum(rate(demo_api_http_requests_total{namespace="demo1"}[5m]))
  )
)
```

If there is no traffic, this ratio has no meaningful value. Generate traffic before interpreting it.

### Latency SLI

95th percentile request duration:

```promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(demo_api_http_request_duration_seconds_bucket{namespace="demo1"}[5m])
  )
)
```

## SLO proposal

| Objective | Target | Measurement window | Error budget |
|---|---:|---|---:|
| Availability | 99.9% successful requests | 30 days | 0.1% of requests may fail |
| Latency | 95% of requests under 500 ms | 30 days | 5% may exceed 500 ms |

The availability error budget gives a practical decision tool: as error budget burns quickly, slow risky releases and focus on reliability. A single restart metric is useful for diagnosis, but user-facing error rate is closer to the SLO.

## Investigation sequence

1. Check error-rate and latency queries in Grafana Explore.
2. Identify whether only one pod has errors: `kubectl get pods -n demo1`.
3. Inspect logs and events for the affected pod.
4. Compare the time of errors with deployments, restarts, and injected traffic.
5. Mitigate user impact, then record the root cause and a corrective action.
