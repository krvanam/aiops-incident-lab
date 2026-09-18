# Day 14: End-to-End Incident Investigation

## Goal

Practice one realistic incident workflow using the observability components you have already built. You will create controlled 5xx traffic for the single `orders-api` service, locate its SLO signal, correlate the request through Loki and Tempo, verify Kubernetes and GitOps state, and record a safe operational decision.

```text
Controlled 500 request
        |
        v
Prometheus SLO signal ---> Grafana dashboard
        |                         |
        v                         v
Kubernetes / Argo CD state --> Loki log --> Tempo trace
                                          |
                                          v
                              Runbook and incident decision
```

## Scope and safety

- This lab reuses the single `orders-api`; do not add another service.
- The traffic uses `?fail=true`, which intentionally returns HTTP 500.
- Treat all investigation commands as read-only.
- Synthetic traffic is the demonstrated cause, so the correct outcome is to stop the traffic. Do **not** restart the Deployment.
- The Day 9 guarded script remains the only lab mechanism for an approved restart. It is not used in this exercise.
- Do not commit generated incident records, credentials, trace IDs from sensitive systems, or production log data.

## Prerequisites

- Days 5, 7, 8, 9, 12, and 13 are working.
- Grafana is accessible locally.
- Argo CD shows `orders-api-gitops` as `Synced / Healthy`.

Start the local port forwards in separate terminals:

```bash
kubectl port-forward -n demo1 svc/orders-api 8081:80
```

```bash
kubectl port-forward -n monitoring \
  svc/monitoring-kube-prometheus-prometheus 9090:9090
```

## Step 1: establish the baseline

Before creating the test signal, confirm the deployment and GitOps state:

```bash
kubectl get deployment/orders-api -n demo1
kubectl get pods -n demo1 -l app=orders-api
kubectl get application -n argocd orders-api-gitops
```

Record the output in [the incident record](templates/orders-api-synthetic-500-incident.md). Your expected baseline is all desired replicas ready and Argo CD `Synced / Healthy`.

## Step 2: generate a controlled incident signal

Run this in a new terminal for approximately two minutes, then stop it with `Ctrl+C`:

```bash
while true; do
  curl -s -o /dev/null 'http://localhost:8081/api/orders?fail=true'
  sleep 2
done
```

While it is running, capture one trace ID separately:

```bash
curl -s -D - -o /dev/null \
  'http://localhost:8081/api/orders?fail=true' \
  | rg -i '^(HTTP|x-trace-id)'
```

This creates application-level failures only. It does not crash pods and it does not require remediation.

## Step 3: investigate the SLO signal

Open the Day 7 **Orders API — Operations Overview** dashboard in Grafana. Observe:

- availability SLI declines;
- 5xx error rate rises;
- the high-error-rate alert can fire after its configured evaluation window;
- p95 latency need not be high for this failure scenario.

Validate the error percentage directly in Prometheus or Grafana Explore:

```promql
100 * (
  sum(rate(demo_api_http_requests_total{namespace="demo1",status_code=~"5.."}[5m]))
  /
  sum(rate(demo_api_http_requests_total{namespace="demo1"}[5m]))
)
```

Record the observed value and time. The metric shows **how much** user-facing failure exists, not its root cause.

## Step 4: verify platform and GitOps state

Use the same time window to rule out an unhealthy rollout or crash loop:

```bash
kubectl get deployment/orders-api -n demo1
kubectl get pods -n demo1 -l app=orders-api
kubectl get events -n demo1 --sort-by=.metadata.creationTimestamp | tail -20
kubectl get application -n argocd orders-api-gitops
```

Expected result: ready pods, no relevant restart/event pattern, and Argo CD remains `Synced / Healthy`. This makes a Deployment restart unsupported by the evidence.

## Step 5: correlate the failing request

In Grafana **Explore**, select **Loki** and query:

```logql
{namespace="demo1", app="orders-api"} |= "event=orders_request" |= "status_code=500"
```

Open a matching line. It contains the method, route, status, duration, and `trace_id`. Select **View trace** to open the associated Tempo trace.

In Tempo, verify:

- service: `orders-api`;
- route: `GET /api/orders`;
- `http.status_code`: `500`;
- error status on the request span.

The metric, log, and trace should describe the same failure mode at different levels:

| Signal | What it proves |
| --- | --- |
| Prometheus | Failure rate and SLO impact over a time window. |
| Loki | One concrete failed request and its structured application evidence. |
| Tempo | The lifecycle and error attributes of that individual request. |

## Step 6: make and document the decision

Stop the synthetic traffic with `Ctrl+C`. Complete [the incident record](templates/orders-api-synthetic-500-incident.md).

Your decision should be:

> The 5xx increase was caused by controlled `?fail=true` traffic. Pods and GitOps state were healthy. Stop the test traffic and allow the Prometheus window to age out; do not restart the Deployment.

Watch the metrics and alert condition fall after the five-minute query window and configured alert duration have elapsed.

## Evidence checklist

- [ ] Baseline Deployment readiness and Argo CD status captured.
- [ ] 5xx percentage observed in Grafana or Prometheus.
- [ ] A `status_code=500` Loki log located.
- [ ] The Loki **View trace** link opened the corresponding Tempo trace.
- [ ] Tempo trace showed `orders-api`, route, and HTTP 500.
- [ ] Synthetic traffic stopped.
- [ ] Incident record completed with the no-restart decision.

## Portfolio talking point

> Executed an end-to-end Kubernetes incident investigation by correlating Prometheus SLO degradation, GitOps and workload health, Loki application logs, and Tempo traces. Applied an evidence-first no-remediation decision for controlled traffic rather than restarting healthy workloads.
