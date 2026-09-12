# Day 7: Grafana Dashboard as Code

## Goal

Provision an Orders API operations dashboard from a Git-tracked Kubernetes
ConfigMap rather than manually building and saving panels in Grafana.

```text
Git dashboard JSON
       |
       v
ConfigMap: grafana_dashboard="1"
       |
       v
Grafana dashboard sidecar
       |
       v
Orders API — Operations Overview
```

## Why Day 7 follows Day 6

Day 6 groups two SLO alerts into one Orders API incident. This dashboard gives
the on-call engineer a single view of the incident: traffic, availability, p95
latency, firing alerts, and restart evidence.

## Dashboard panels

| Panel | Operational question |
|---|---|
| Availability SLI | Are users receiving successful responses? |
| 5xx Error Rate | Is the availability SLO alert condition present? |
| p95 Latency | Is the latency SLO alert condition present? |
| Firing Orders API SLO Alerts | Which Day 5 symptoms are firing right now? |
| Request Rate by Status Code | Is the impact broad, and are errors increasing? |
| p95 Latency Trend | When did latency begin to degrade? |
| Container Restarts | Is Kubernetes instability a plausible contributing cause? |

## Deploy

The existing Grafana sidecar watches ConfigMaps labelled
`grafana_dashboard: "1"` across namespaces. Deploy the ConfigMap into the
`monitoring` namespace:

```bash
kubectl apply -f dashboard/10-orders-api-operations-dashboard.yaml
kubectl get configmap -n monitoring orders-api-operations-dashboard
```

## Open Grafana

Port-forward Grafana in one terminal:

```bash
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
```

Open `http://localhost:3000`, then use **Dashboards** and search for:

```text
Orders API — Operations Overview
```

The dashboard sidecar may take up to one minute to provision a newly labelled
ConfigMap. Refresh Grafana before concluding that it is absent.

## Validate with controlled traffic

Keep the Day 4 Orders API port-forward running:

```bash
kubectl port-forward -n demo1 svc/orders-api 8081:80
```

Generate mixed traffic in another terminal for two to three minutes:

```bash
while true; do
  curl -s -o /dev/null http://localhost:8081/api/orders
  curl -s -o /dev/null 'http://localhost:8081/api/orders?fail=true'
  curl -s -o /dev/null 'http://localhost:8081/api/orders?delay_ms=800'
  sleep 2
done
```

Expected outcome:

- Availability falls and 5xx error rate rises.
- p95 latency exceeds `0.5 s`.
- The Day 5 firing-alert panel reaches `2` after the alert `for: 2m` delay.
- Request rate separates HTTP 200 and HTTP 500 series.

Stop the traffic loop with `Ctrl+C` when you have observed the behavior.

## Completion checks

```bash
kubectl get configmap -n monitoring orders-api-operations-dashboard
kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana
```

You have completed Day 7 when the provisioned dashboard visualizes normal and
degraded Orders API behavior and you can use it with the Day 5 and Day 6
runbooks. See the [dashboard runbook](runbooks/orders-api-dashboard.md) for
the incident workflow.
