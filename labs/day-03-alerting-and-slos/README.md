# Day 3: Prometheus Alerting and SLO Foundations

## Goal

Turn a Kubernetes signal into an actionable alert. You will deploy a `PrometheusRule`, deliberately restart one NGINX container, observe the alert lifecycle, and use a runbook to establish root cause.

## What you will learn

- A metric becomes useful operationally only when its threshold, duration, severity, ownership, and response are clear.
- Prometheus evaluates alert rules every 30 seconds in this cluster.
- `for: 1m` prevents a brief, one-time metric change from immediately becoming a firing alert.
- Alert labels carry routing and ownership context; annotations give responders human-readable context and a runbook.
- An SLO defines the reliability outcome users expect. Alerts should protect that outcome, not merely report every technical event.

## Rule design

The alert rule is in `manifests/10-nginx-pod-restart-alert.yaml`.

```text
Container restart counter increases
        |
        v
Prometheus evaluates every 30 seconds
        |
        v
Condition true for one minute = Firing
        |
        v
Alertmanager / Grafana shows alert and links to runbook
```

The query detects one or more restarts in the last five minutes:

```promql
sum by (namespace, pod, container) (
  increase(kube_pod_container_status_restarts_total{
    namespace="demo1",
    container="nginx"
  }[5m])
) > 0
```

This is deliberately a learning alert. A production alert would usually account for impact: restart frequency, unavailable replicas, error rate, and the service's SLO.

## Prerequisites

```bash
export KUBECONFIG="$HOME/.kube/aiops-lab-kind.yaml"
kubectl get nodes
kubectl get pods -n monitoring
kubectl get deployment nginx-demo1 -n demo1
```

Expected result: the monitoring pods are running and `nginx-demo1` has two available replicas.

## Deploy the alert rule

```bash
kubectl apply -f manifests/10-nginx-pod-restart-alert.yaml
kubectl get prometheusrule -n monitoring demo1-nginx-alerts
kubectl describe prometheusrule -n monitoring demo1-nginx-alerts
```

The required `release: monitoring` label matches your installed Prometheus `ruleSelector`, so Prometheus can discover this rule.

## Open the alert interfaces

Prometheus rules and alerts interface:

```bash
kubectl port-forward -n monitoring \
  svc/monitoring-kube-prometheus-prometheus 9090:9090
```

Open `http://localhost:9090/rules` and later `http://localhost:9090/alerts`.

In another terminal, open Alertmanager:

```bash
kubectl port-forward -n monitoring \
  svc/monitoring-kube-prometheus-alertmanager 9093:9093
```

Open `http://localhost:9093`.

## Trigger the alert safely

This only affects one replica in your local learning cluster.

```bash
POD_NAME=$(kubectl get pods -n demo1 -l app=nginx-demo1 \
  -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n demo1 "$POD_NAME" -- sh -c 'kill 1'
kubectl get pods -n demo1 -w
```

Wait for the container to restart, then allow approximately two to three minutes for a Prometheus scrape, rule evaluation, and the one-minute `for` period.

Expected lifecycle:

1. The restarted pod's `RESTARTS` column increments.
2. The alert appears as **Pending** in Prometheus.
3. It becomes **Firing** after the condition has held for one minute.
4. It remains active while the five-minute query window contains that restart, then resolves automatically.

## Validate from the command line

```bash
kubectl get pods -n demo1
kubectl get events -n demo1 --sort-by=.metadata.creationTimestamp
kubectl logs -n demo1 "$POD_NAME" --previous --timestamps
```

Use Grafana Explore with:

```promql
sum by (pod, container) (
  increase(kube_pod_container_status_restarts_total{namespace="demo1"}[5m])
)
```

Then follow the [pod restart runbook](runbooks/nginx-pod-restart.md).

## SLO connection

For a user-facing service, a practical starting SLO might be: **99.9% successful requests over 30 days**. Its error budget is the permitted 0.1% failure rate.

This restart alert is a leading technical signal, not an SLO alert by itself. The next step will be to expose an application metric and use availability, latency, or error rate to define an SLI and SLO.

## Completion checks

```bash
kubectl get prometheusrule -n monitoring demo1-nginx-alerts
kubectl get pods -n demo1
kubectl get events -n demo1 --sort-by=.metadata.creationTimestamp
```

You have completed Day 3 when you can explain the alert expression, observe it transition from pending to firing, identify the restarted container, and use the runbook to distinguish a graceful restart from a failure.
