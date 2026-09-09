# Day 5: SLO-Based Application Alerting

## Goal

Convert the Day 4 application SLIs into alerts that indicate a meaningful user-facing reliability problem.

## Why this is different from a pod-restart alert

```text
Pod restart alert:       "A technical component changed state."
SLO availability alert: "Users are receiving too many failed responses."
SLO latency alert:      "Too many users are experiencing slow responses."
```

All three signals are valuable. SLO-based alerts prioritize impact, while infrastructure alerts help diagnose the cause.

## Alert design

| Alert | Expression | Delay | Purpose |
|---|---|---:|---|
| `OrdersApiHighErrorRate` | 5xx request rate >5% | 2 min | Detect a sustained availability degradation. |
| `OrdersApiHighP95Latency` | p95 request duration >500 ms | 2 min | Detect a sustained latency degradation. |

The alert rules have `release: monitoring`, matching the Prometheus `ruleSelector` configured by your Helm release.

## Deploy

```bash
kubectl apply -f manifests/10-orders-api-slo-alerts.yaml
kubectl get prometheusrule -n monitoring orders-api-slo-alerts
```

Open Prometheus Rules at `http://localhost:9090/rules`. Find the group `demo1.orders-api.slo`; both alerts should initially be inactive.

## Trigger the error-rate alert

Keep the Day 4 application port-forward running (`localhost:8081`). In another terminal, generate sustained failed traffic for about three minutes:

```bash
while true; do
  curl -s http://localhost:8081/api/orders > /dev/null
  curl -s -o /dev/null 'http://localhost:8081/api/orders?fail=true'
  sleep 5
done
```

After two to three minutes, open `http://localhost:9090/alerts`. `OrdersApiHighErrorRate` should progress from **Pending** to **Firing**.

Stop the traffic loop with `Ctrl+C` when you have observed the alert.

## Trigger the latency alert

Generate only slow but successful requests for about three minutes:

```bash
while true; do
  curl -s 'http://localhost:8081/api/orders?delay_ms=750' > /dev/null
  sleep 2
done
```

After two to three minutes, `OrdersApiHighP95Latency` should progress from **Pending** to **Firing**.

## Verify in Alertmanager

Keep the Alertmanager port-forward running:

```bash
kubectl port-forward -n monitoring \
  svc/monitoring-kube-prometheus-alertmanager 9093:9093
```

Open `http://localhost:9093` and filter by `service="orders-api"`.

## Investigate and resolve

Use the [SLO breach runbook](runbooks/orders-api-slo-breach.md). The alerts automatically resolve after the five-minute metric window no longer includes the injected traffic.

## Completion checks

```bash
kubectl get prometheusrule -n monitoring orders-api-slo-alerts
kubectl get pods -n demo1 -l app=orders-api
```

You have completed Day 5 when both alerts have fired at least once, arrived in Alertmanager, and you can explain the difference between a service-level symptom and its underlying infrastructure cause.
