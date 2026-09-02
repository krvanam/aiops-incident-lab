# AIOps Incident Intelligence Lab

A hands-on Kubernetes, observability, and AIOps portfolio project.

## Day 1 outcome

Day 1 establishes a local Kind cluster and deploys NGINX through a Kubernetes Service.

```text
Colima / Docker
       |
       v
Kind cluster: aiops-lab
       |
       +-- Namespace: demo1
       |      +-- Deployment: nginx-demo1
       |      +-- Service: nginx-demo1-svc (NodePort)
       |      +-- ConfigMap: nginx-demo1-html
       |
       +-- Namespace: monitoring (used on Day 2)
```

## Prerequisites

- Docker engine running through Colima.
- Kind, Helm, Git, and the standalone `kubectl` client installed.
- The Minikube `kubectl` alias removed or disabled.

## Connect to the local cluster

```bash
export KUBECONFIG="$HOME/.kube/aiops-lab-kind.yaml"
kubectl config current-context
kubectl get nodes
```

Expected context: `kind-aiops-lab`.

## Deploy Day 1 application

```bash
kubectl apply -f k8s/
kubectl get all -n demo1
kubectl get endpointslice -n demo1 \
  -l kubernetes.io/service-name=nginx-demo1-svc
```

Access NGINX locally:

```bash
kubectl port-forward -n demo1 svc/nginx-demo1-svc 8080:80
```

Open `http://localhost:8080` or run `curl http://localhost:8080` from another terminal.

## Learning documentation

- [Day 1 guide](docs/day-1-kubernetes-lab.md)
- [Image pull failure runbook](runbooks/image-pull-backoff.md)
- [Day 2 monitoring plan](docs/day-2-prometheus-grafana.md)

## Safety

This project is a local learning lab. Do not commit passwords, API tokens, customer data, kubeconfig files, or cloud credentials.

