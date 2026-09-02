# Day 1: Kubernetes Foundations Lab

## What was learned

- Kind runs Kubernetes nodes as Docker containers.
- Docker client availability is different from Docker engine availability.
- `kubectl` manages Kubernetes resources; `kind` manages Kind clusters and nodes.
- `KUBECONFIG` decides which Kubernetes cluster `kubectl` connects to.
- A Service selects backend pods through labels and routes traffic to them.
- `NodePort` exposes a Service on a Kubernetes node port; it does not automatically make a local laptop application public on the internet.
- `kubectl describe` shows the current resource state; `kubectl get events` provides useful recent failure history.

## Cluster creation

```bash
kind create cluster --name aiops-lab
kind export kubeconfig --name aiops-lab \
  --kubeconfig "$HOME/.kube/aiops-lab-kind.yaml"
export KUBECONFIG="$HOME/.kube/aiops-lab-kind.yaml"
kubectl get nodes
```

## Essential inspection commands

```bash
kubectl get nodes -o wide
kubectl get namespaces
kubectl get pods -A
kubectl describe pod <pod-name> -n <namespace>
kubectl get events -n <namespace> --sort-by=.metadata.creationTimestamp
```

## Deploy the NGINX lab

```bash
kubectl apply -f k8s/
kubectl rollout status deployment/nginx-demo1 -n demo1
kubectl get service nginx-demo1-svc -n demo1
kubectl get endpointslice -n demo1 \
  -l kubernetes.io/service-name=nginx-demo1-svc
```

## Service flow

```text
Browser / curl
       |
localhost:8080 through port-forward
       |
Service: nginx-demo1-svc:80
       |
EndpointSlice: NGINX pod IPs on port 80
       |
NGINX containers
```

## Test access

```bash
kubectl port-forward -n demo1 svc/nginx-demo1-svc 8080:80
```

In a second terminal:

```bash
curl http://localhost:8080
```

## Troubleshooting drill

Create a pod with an invalid image tag, then investigate it:

```bash
kubectl create namespace troubleshooting
kubectl run broken-app \
  --image=nginx:this-image-does-not-exist \
  --namespace troubleshooting
kubectl describe pod broken-app -n troubleshooting
kubectl get events -n troubleshooting --sort-by=.metadata.creationTimestamp
```

Expected root cause: the image tag does not exist, resulting in `ErrImagePull` and then `ImagePullBackOff`.

