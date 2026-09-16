# Day 13: Centralized Logs and Trace Correlation

This lab completes the three core observability signals for the local Orders API:

- metrics in Prometheus;
- traces in Tempo;
- logs in Loki.

Grafana Alloy discovers only `orders-api` pods in the `demo1` namespace, streams their container logs through the Kubernetes API, and sends them to Loki. The application writes an operational log line containing the same trace ID returned in `X-Trace-Id`.

```text
Orders API stdout
       |
       v
Grafana Alloy -- Kubernetes API discovery and pod log stream
       |
       v
Loki ---- Grafana Explore ---- Tempo trace link
```

## Scope and safety

- This is a single-service, local Kind lab.
- Loki keeps data in `emptyDir`; deleting its pod removes collected logs.
- Alloy is restricted to reading pod metadata and pod logs. It does not change workloads.
- The collector deliberately targets only `demo1/orders-api`, preventing noisy collection of every cluster workload.
- Do not put tokens, kubeconfig data, or customer data into log lines.

## Objects created

| Object | Purpose |
| --- | --- |
| `Namespace/logs` | Separates the centralized logging components. |
| `ConfigMap/loki-config` | Loki local-storage and retention configuration. |
| `Deployment/loki` and `Service/loki` | Runs the queryable log store and stable in-cluster endpoint. |
| `ServiceAccount`, `ClusterRole`, `ClusterRoleBinding` | Grants Alloy read-only pod discovery and log access. |
| `ConfigMap/alloy-config` | Defines the selective discovery, labels, and Loki export pipeline. |
| `Deployment/alloy-log-collector` | Runs one Alloy collector for the selected Orders API pod logs. |
| `ConfigMap/loki-datasource` | Grafana sidecar provisions Loki and its Tempo trace link. |

## Step 1: deploy Loki, Alloy, and the Grafana datasource

```bash
cd /Users/krvanam/AI-Projects/aiops-incident-lab

kubectl apply -f labs/day-13-centralized-logging/logs/
kubectl apply -f labs/day-13-centralized-logging/grafana/

kubectl rollout status deployment/loki -n logs
kubectl rollout status deployment/alloy-log-collector -n logs
kubectl get pods -n logs
```

## Step 2: build and load the logging-enabled Orders API

The Day 13 application change produces `aiops-orders-api:v3`. Build and load it **before** pushing its manifest change, so Argo CD never deploys an unavailable local image.

```bash
docker build -t aiops-orders-api:v3 labs/day-04-application-sli-slo/app/
kind load docker-image aiops-orders-api:v3 --name aiops-lab
docker exec aiops-lab-control-plane crictl images | rg 'aiops-orders-api'
```

Commit and push the Day 13 change. Argo CD then rolls the existing `orders-api` Deployment to v3:

```bash
kubectl rollout status deployment/orders-api -n demo1
kubectl get deployment orders-api -n demo1 \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\\n"}'
```

Expected image: `aiops-orders-api:v3`.

## Step 3: create a trace-correlated log line

Keep this in one terminal:

```bash
kubectl port-forward -n demo1 svc/orders-api 8081:80
```

From another terminal, generate a slow request and capture its trace ID:

```bash
curl -s -D - -o /dev/null \
  'http://localhost:8081/api/orders?delay_ms=900' \
  | rg -i '^(HTTP|x-trace-id)'
```

Generate a controlled failure:

```bash
curl -s -D - -o /dev/null \
  'http://localhost:8081/api/orders?fail=true' \
  | rg -i '^(HTTP|x-trace-id)'
```

Wait 10–20 seconds for collection, then open Grafana → **Explore** → **Loki**. Query:

```logql
{namespace="demo1", app="orders-api"} |= "event=orders_request"
```

Select the generated **View trace** link from `trace_id=...` to pivot to Tempo.

## Troubleshooting

```bash
kubectl get pods -n logs
kubectl logs deployment/alloy-log-collector -n logs --tail=100
kubectl logs deployment/loki -n logs --tail=100
kubectl auth can-i get pods/log --as=system:serviceaccount:logs:alloy-log-collector -A
```

Use the [log and trace runbook](runbooks/log-trace-investigation.md) to distinguish a collection failure from an application failure.
