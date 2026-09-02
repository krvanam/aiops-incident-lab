# Day 2 Preview: Prometheus and Grafana

## Goal

Install the `kube-prometheus-stack` Helm chart in the `monitoring` namespace, inspect its pods, access Grafana locally, and learn the difference between metrics, logs, and traces.

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

Access Grafana after the pods are ready:

```bash
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
```

Get the admin password in a separate terminal:

```bash
kubectl get secret -n monitoring monitoring-grafana \
  -o jsonpath="{.data.admin-password}" | base64 --decode
```

