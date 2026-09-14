# Day 8: GitOps with Argo CD

## Goal

Use Argo CD to make Git the desired state for the Orders API. Argo CD watches this repository and reconciles the Day 4 Kubernetes manifests into the local Kind cluster.

```text
GitHub repository (main)
  labs/day-04-application-sli-slo/k8s
                 |
                 v
    Argo CD Application: orders-api-gitops
                 |
                 v
Kind cluster / namespace demo1
  Deployment + Service + ServiceMonitor
```

## What this lab manages

The `orders-api-gitops` Application reads the existing Day 4 manifest directory and manages:

- `Deployment/orders-api`
- `Service/orders-api`
- `ServiceMonitor/orders-api`

It uses automated sync and self-healing. Pruning is deliberately disabled: deleting a manifest from Git will **not** delete the corresponding cluster object in this lab.

The Day 4 resources already exist. On the first sync, Argo CD adopts their desired configuration and adds its tracking metadata; it should not recreate the workload.

## Prerequisites

- Kind cluster is running and `kubectl get nodes` succeeds.
- Day 4 Orders API is present in `demo1`.
- This public GitHub repository is reachable from the Kind cluster.

```bash
export KUBECONFIG="$HOME/.kube/aiops-lab-kind.yaml"
kubectl get deployment,service,servicemonitor -n demo1 -l app=orders-api
```

## 1. Install Argo CD

This local lab follows the official Argo CD installation manifest. It installs cluster controllers and CRDs, so use a learning cluster only.

```bash
kubectl create namespace argocd

kubectl apply -n argocd --server-side --force-conflicts \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

kubectl wait --for=condition=Available deployment --all -n argocd --timeout=5m
kubectl get pods -n argocd
```

Expected: the Argo CD deployments become `Available` and their pods become `Running`.

## 2. Create the GitOps Application

```bash
kubectl apply -f application/10-orders-api-gitops-application.yaml

kubectl get application -n argocd orders-api-gitops -w
```

Wait until the Application reports `Synced` and `Healthy`, then stop the watch with `Ctrl+C`.

Check the status without watching:

```bash
kubectl get application -n argocd orders-api-gitops \
  -o jsonpath='{.status.sync.status}{" / "}{.status.health.status}{"\n"}'
```

Expected output: `Synced / Healthy`.

## 3. Open the Argo CD UI

In one terminal:

```bash
kubectl port-forward -n argocd svc/argocd-server 8080:443
```

Open `https://localhost:8080`. Your browser will warn about the local self-signed certificate; proceed only because this is your local cluster.

Sign in as `admin`. Retrieve the one-time initial password locally; do not commit or share it:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo
```

In the UI, open **orders-api-gitops** and inspect the resource tree. It should show the Deployment, Service, and ServiceMonitor in `demo1`.

## 4. Prove self-healing

Create safe configuration drift by changing replicas outside Git:

```bash
kubectl scale deployment/orders-api -n demo1 --replicas=1
kubectl get deployment/orders-api -n demo1 -w
```

Argo CD should restore the Git-declared value of `2` replicas. This can take a short reconciliation interval. Stop the watch after it returns to `2/2` with `Ctrl+C`.

Confirm the source of truth remains Git:

```bash
git show main:labs/day-04-application-sli-slo/k8s/10-orders-api.yaml | rg 'replicas:'
```

## Evidence to capture

- `kubectl get application -n argocd orders-api-gitops` shows `Synced` and `Healthy`.
- Argo CD UI shows the three managed Day 4 resources.
- After a manual scale to one replica, the Deployment returns to two replicas without a manual `kubectl apply`.

## Safety boundary

- Do not add credentials or tokens to the Application: the repository is public.
- Do not enable `prune` yet. That lesson comes after reviewing deletion impact.
- Do not point this local Application at a production cluster or a production Git branch.

## Troubleshooting

See [the application runbook](runbooks/argocd-application.md).
