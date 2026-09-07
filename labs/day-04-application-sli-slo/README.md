# Day 4: Application Metrics, SLIs, and SLOs

## Goal

Deploy an instrumented FastAPI orders service. Prometheus will scrape its custom metrics, and you will use request outcomes and latency to calculate service-level indicators (SLIs).

## Architecture

```text
Traffic generator / browser
          |
          v
Service: orders-api:80
          |
          v
FastAPI pods (2)
  +-- /api/orders       request counter + duration histogram
  +-- /health           Kubernetes probes
  +-- /metrics          Prometheus metrics
          |
          v
ServiceMonitor -> Prometheus -> Grafana
```

## Build and load the local image

Run these commands from this Day 4 folder:

```bash
docker build -t aiops-orders-api:v1 app/
kind load docker-image aiops-orders-api:v1 --name aiops-lab
```

`kind load docker-image` makes your Mac's local Docker image available to the Kind node, so no public registry is required.

## Deploy the application and ServiceMonitor

```bash
kubectl apply -f k8s/
kubectl rollout status deployment/orders-api -n demo1
kubectl get pods,service,servicemonitor -n demo1
```

Verify that the Service selects two ready endpoints:

```bash
kubectl get endpointslice -n demo1 \
  -l kubernetes.io/service-name=orders-api
```

## Test the application

In one terminal:

```bash
kubectl port-forward -n demo1 svc/orders-api 8081:80
```

In another terminal, create normal traffic:

```bash
for i in {1..20}; do
  curl -s http://localhost:8081/api/orders > /dev/null
done
```

Inject five controlled errors:

```bash
for i in {1..5}; do
  curl -s -o /dev/null -w '%{http_code}\n' \
    'http://localhost:8081/api/orders?fail=true'
done
```

Inject controlled latency to make the latency histogram visible:

```bash
for i in {1..5}; do
  curl -s http://localhost:8081/api/orders?delay_ms=750 > /dev/null
done
```

Check that the service exposes metrics:

```bash
curl -s http://localhost:8081/metrics | grep demo_api
```

## Confirm Prometheus scraping

Wait at least 30–60 seconds after deployment. In Prometheus, open `http://localhost:9090/targets` and find the `orders-api` target. Its state should be **UP**.

Or use Grafana Explore with:

```promql
sum by (status_code) (
  rate(demo_api_http_requests_total{namespace="demo1"}[5m])
)
```

## Calculate the SLIs

Use the queries in the [SLI/SLO reference](runbooks/orders-api-sli-slo.md):

- Availability: percentage of non-5xx responses.
- Latency: 95th percentile duration from the histogram.

For this lab, propose a 30-day SLO of **99.9% availability** and **95% of requests below 500 ms**. Your injected failures and 750 ms requests deliberately show how error rate and latency consume those reliability objectives.

## Completion checks

```bash
kubectl get pods -n demo1 -l app=orders-api
kubectl get servicemonitor -n demo1 orders-api
kubectl get endpointslice -n demo1 -l kubernetes.io/service-name=orders-api
```

You have completed Day 4 when both API pods are ready, Prometheus marks the target UP, Grafana shows normal/error/slow requests, and you can explain how the availability and latency SLIs relate to the SLO.
