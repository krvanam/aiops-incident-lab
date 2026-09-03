# Day 2: Prometheus, Grafana, and Pod Restart Investigation

## Goal

Install the `kube-prometheus-stack` Helm chart in the `monitoring` namespace, inspect cluster and workload metrics in Grafana, and investigate a controlled container restart.

## What we learned

- `kube-prometheus-stack` installs Prometheus, Grafana, Alertmanager, kube-state-metrics, node exporter, and the Prometheus Operator.
- Prometheus collects time-series metrics. Grafana queries and visualizes them. Container logs provide diagnostic detail that a metric alone cannot.
- The local Kind cluster has one node. Kubernetes dashboards show workload resource consumption for selected namespaces and pods.
- A Deployment with two replicas creates two running pods and the Service EndpointSlice contains both ready pod IP addresses.
- CPU and memory requests influence scheduling; limits cap usage. CPU above its limit is throttled, while memory above its limit can lead to `OOMKilled`.
- A container restart keeps the same pod name and increments its `RESTARTS` value. A rollout, scale event, or deletion creates/removes pods and normally produces new pod names.
- `kubectl logs --previous` reads the terminated container instance. `.lastState.terminated` supplies its reason, exit code, and timestamps. Events provide the Kubernetes lifecycle timeline.

## Lab environment

```text
Kind cluster: aiops-lab
|
+-- namespace: monitoring
|   +-- Helm release: monitoring
|       +-- Prometheus
|       +-- Grafana
|       +-- Alertmanager
|       +-- kube-state-metrics
|       +-- node exporter
|
+-- namespace: demo1
    +-- Deployment: nginx-demo1 (2 replicas)
    +-- Service: nginx-demo1-svc
```

## Preparation

```bash
export KUBECONFIG="$HOME/.kube/aiops-lab-kind.yaml"
kubectl get nodes
kubectl get namespace monitoring
helm version
```

## Day 2 commands

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring

kubectl get pods -n monitoring -w
```

The chart was installed successfully as release `monitoring` in the `monitoring` namespace. Confirm it at any time:

```bash
helm list -n monitoring
kubectl get pods -n monitoring
```

Expected healthy components include Grafana, Prometheus, Alertmanager, kube-state-metrics, node exporter, and the Prometheus Operator.

Access Grafana after the pods are ready:

```bash
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
```

Get the admin password in a separate terminal:

```bash
kubectl get secret -n monitoring monitoring-grafana \
  -o jsonpath="{.data.admin-password}" | base64 --decode
```

Open `http://localhost:3000`, then use the Kubernetes dashboards to inspect the cluster, namespace, and pod views.

## Metrics observed

- One ready Kind control-plane node.
- Kubernetes system pods running in `kube-system`.
- NGINX workload running in namespace `demo1`.
- Low baseline CPU and memory use, which is normal for this local lab.

Resource usage is not the same as configuration. Inspect resource requests and limits from the workload manifest:

```bash
kubectl describe deployment nginx-demo1 -n demo1
```

## Pod restart analysis

List current restart counts:

```bash
kubectl get pods -n demo1
```

Use this PromQL query in Grafana Explore to see the total restart counter per pod and container:

```promql
sum by (pod, container) (
  kube_pod_container_status_restarts_total{namespace="demo1"}
)
```

To see restarts that occurred during the last five minutes:

```promql
sum by (pod, container) (
  increase(kube_pod_container_status_restarts_total{namespace="demo1"}[5m])
)
```

### Controlled restart performed

We deliberately terminated PID 1 (the NGINX main process) in one replica. This is safe in this disposable local lab because the Deployment restarts the container.

```bash
kubectl exec -n demo1 nginx-demo1-7dcc8f7fd9-6pbvl -- sh -c 'kill 1'
```

Observed result for `nginx-demo1-7dcc8f7fd9-6pbvl`:

```text
RESTARTS: 1
Reason: Completed
Exit code: 0
```

`kill 1` allowed NGINX to shut down gracefully, which explains `Completed` and exit code `0`. Kubernetes then started the container again because it is managed by a Deployment (`restartPolicy: Always`). This was not an OOM, image-pull, or probe failure.

### Investigation checklist

```bash
# Logs from the terminated instance
kubectl logs -n demo1 nginx-demo1-7dcc8f7fd9-6pbvl --previous --timestamps

# Exact termination state
kubectl get pod -n demo1 nginx-demo1-7dcc8f7fd9-6pbvl \
  -o jsonpath='Reason: {.status.containerStatuses[0].lastState.terminated.reason}{"\\n"}Exit code: {.status.containerStatuses[0].lastState.terminated.exitCode}{"\\n"}Started: {.status.containerStatuses[0].lastState.terminated.startedAt}{"\\n"}Finished: {.status.containerStatuses[0].lastState.terminated.finishedAt}{"\\n"}'

# Lifecycle events, oldest to newest
kubectl get events -n demo1 --sort-by=.metadata.creationTimestamp
```

The previous NGINX logs showed repeated `kube-probe` requests returning HTTP `200`. These were successful readiness and liveness checks, not errors.

## Exit-code quick reference

| Signal/result | What it usually means | Next investigation step |
|---|---|---|
| `Completed`, exit `0` | Process exited cleanly | Check deployment, scheduled termination, or application shutdown logic. |
| Exit `143` | Process received `SIGTERM` | Check rollout, scale-down, manual termination, or node shutdown. |
| Exit `137` / `OOMKilled` | Process was forcibly killed or exceeded memory | Check limits, usage, and kernel/OOM events. |
| `Error` | Application or command failed | Inspect `--previous` logs and application configuration. |

## Day 2 completion checks

```bash
kubectl get nodes
helm list -n monitoring
kubectl get pods -n monitoring
kubectl get deployment,pods,endpointslice -n demo1
```
