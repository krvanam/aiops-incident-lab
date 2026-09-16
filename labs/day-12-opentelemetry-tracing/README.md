# Day 12: OpenTelemetry Tracing

## Goal

Add traces to the Orders API and investigate them in Grafana. Metrics tell you that latency or errors occurred; a trace shows the lifecycle of one request.

```text
Orders API
  OpenTelemetry FastAPI instrumentation
              |
              | OTLP/gRPC
              v
OpenTelemetry Collector (tracing namespace)
              |
              | OTLP/gRPC
              v
Tempo (local, ephemeral storage)
              |
              v
Grafana Explore: Tempo datasource
```

## What changes

- The API exports traces only when `OTEL_EXPORTER_OTLP_ENDPOINT` is configured.
- The Day 12 Deployment configuration points to the in-cluster collector.
- Business endpoint responses include `X-Trace-Id`.
- Tempo and the Collector run one small local replica each in `tracing`.
- Grafana receives a Tempo datasource through a ConfigMap.

## Safety boundary

- This is a local lab. Tempo uses `emptyDir` storage and retains no durable history.
- Only trace metadata such as service, route, status, and duration is sent. Do not add request bodies, tokens, or customer data as span attributes.
- Tracing does not perform remediation. Continue to use the Day 9 approval gate for any change.

## 1. Deploy the local tracing stack

```bash
cd /Users/krvanam/AI-Projects/aiops-incident-lab/labs/day-12-opentelemetry-tracing

kubectl apply -f tracing/
kubectl apply -f grafana/

kubectl rollout status deployment/tempo -n tracing --timeout=120s
kubectl rollout status deployment/otel-collector -n tracing --timeout=120s
kubectl get pods -n tracing
```

Expected: one `tempo` pod and one `otel-collector` pod are `Running`.

## 2. Build and load the traced application image

Run these steps before pushing the Day 4 Deployment change to Git. Argo CD will reconcile the image tag only after the image is already available inside Kind.

```bash
cd /Users/krvanam/AI-Projects/aiops-incident-lab

docker build -t aiops-orders-api:v2 labs/day-04-application-sli-slo/app/
kind load docker-image aiops-orders-api:v2 --name aiops-lab

docker exec aiops-lab-control-plane crictl images | rg 'aiops-orders-api'
```

## 3. Reconcile the traced application through GitOps

The modified Day 4 Deployment uses image `aiops-orders-api:v2` and configures the OTLP collector endpoint. Commit and push the Day 12 application changes, then watch Argo CD:

```bash
kubectl get application -n argocd orders-api-gitops -w
kubectl get deployment/orders-api -n demo1 -w
```

Expected final state: Argo CD is `Synced / Healthy` and the Deployment has all desired replicas available.

## 4. Generate and inspect a trace

Expose the API:

```bash
kubectl port-forward -n demo1 svc/orders-api 8081:80
```

In another terminal, send one controlled slow request and capture its trace ID:

```bash
curl -s -D - -o /dev/null 'http://localhost:8081/api/orders?delay_ms=900' \
  | rg -i '^(HTTP|x-trace-id)'
```

Open Grafana → **Explore** → datasource **Tempo**, then paste the `X-Trace-Id` value. The trace should show the `orders-api` service and the `GET /api/orders` request duration.

You can also issue a controlled error:

```bash
curl -s -D - -o /dev/null 'http://localhost:8081/api/orders?fail=true' \
  | rg -i '^(HTTP|x-trace-id)'
```

## 5. Troubleshoot

See [the trace investigation runbook](runbooks/trace-investigation.md).

## Evidence to capture

- Tempo datasource works in Grafana.
- A trace ID is returned by the API.
- Grafana trace includes service name, route, duration, and HTTP status.
- A slow trace agrees with the existing p95 latency metric.
