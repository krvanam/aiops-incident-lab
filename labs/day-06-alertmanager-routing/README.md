# Day 6: Alertmanager Routing and Noise Reduction

## Goal

Turn the two Day 5 SLO symptoms into one actionable incident group:

```text
OrdersApiHighErrorRate  ┐
                         ├── team=platform, service=orders-api
OrdersApiHighP95Latency ┘         │
                                  v
                       platform-training receiver
```

The receiver is intentionally credential-free and local. It proves routing and
grouping behavior; it does not send Slack, email, or PagerDuty notifications.

## Why Day 6 follows Day 5

Day 5 proved that Prometheus can detect availability and latency SLO breaches.
Without routing, each symptom can become a separate notification. Day 6 teaches
how Alertmanager uses labels to send related symptoms to the correct owning
team as one service incident.

## Before you begin

Make sure Day 5's `orders-api-slo-alerts` PrometheusRule exists and the local
cluster is healthy:

```bash
kubectl get nodes
kubectl get prometheusrule -n monitoring orders-api-slo-alerts
helm list -n monitoring
```

## Inspect the change before applying it

This lab changes only the Alertmanager configuration in the existing Helm
release. It pins the chart version already installed in this lab.

```bash
helm upgrade monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 88.6.2 \
  --reuse-values \
  --values config/alertmanager-routing-values.yaml \
  --dry-run
```

## Apply the local routing configuration

```bash
helm upgrade monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 88.6.2 \
  --reuse-values \
  --values config/alertmanager-routing-values.yaml \
  --wait

kubectl rollout status \
  statefulset/alertmanager-monitoring-kube-prometheus-alertmanager \
  -n monitoring
```

## Validate the loaded configuration

Port-forward Alertmanager in one terminal:

```bash
kubectl port-forward -n monitoring \
  svc/monitoring-kube-prometheus-alertmanager 9093:9093
```

Open `http://localhost:9093/#/status` and confirm the route contains:

- receiver: `platform-training`
- matchers: `team="platform"`, `service="orders-api"`
- group labels: `team`, `service`
- `group_wait`: `15s`

## Validate grouping

Use the Day 5 traffic exercise to fire both alerts at the same time. In
Alertmanager (`http://localhost:9093`), the two alerts should appear together
under the `platform-training` receiver and have the same group labels.

```bash
# Terminal 1: keep the Orders API port-forward open.
kubectl port-forward -n demo1 svc/orders-api 8081:80

# Terminal 2: create both SLO violations for at least three minutes.
while true; do
  curl -s -o /dev/null 'http://localhost:8081/api/orders?fail=true'
  curl -s -o /dev/null 'http://localhost:8081/api/orders?delay_ms=800'
  sleep 2
done
```

Stop the loop with `Ctrl+C` once both alerts fire. They resolve only after the
five-minute PromQL rate window no longer contains the injected traffic.

## Completion checks

```bash
helm get values monitoring -n monitoring -a | rg -n -C 3 \
  'platform-training|group_wait|group_by'

kubectl get pods -n monitoring
```

You have completed Day 6 when both Day 5 alerts are firing, Alertmanager shows
the `platform-training` route, and you can explain the difference between
grouping, routing, and inhibition. See the [routing runbook](runbooks/alert-routing-and-grouping.md)
for the operational workflow.
