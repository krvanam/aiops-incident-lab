# Runbook: Troubleshoot the Orders API GitOps Application

## Fast status check

```bash
kubectl get application -n argocd orders-api-gitops
kubectl describe application -n argocd orders-api-gitops
```

Interpret the two main states separately:

| State | Meaning | First action |
|---|---|---|
| `Synced` | Live resources match the Git revision Argo CD evaluated. | Check `Healthy` separately. |
| `OutOfSync` | Git and live state differ, or the sync has not completed. | Inspect Application events and controller logs. |
| `Healthy` | The managed Kubernetes resources report healthy. | Verify the workload endpoints if needed. |
| `Degraded` | A managed resource is failing health checks. | Inspect the named workload in `demo1`. |

## Application is OutOfSync

```bash
kubectl describe application -n argocd orders-api-gitops
kubectl logs -n argocd deploy/argocd-application-controller --tail=100
kubectl get deployment,service,servicemonitor -n demo1 -l app=orders-api
```

Check that the source details are exactly:

- Repository: `https://github.com/krvanam/aiops-incident-lab.git`
- Revision: `main`
- Path: `labs/day-04-application-sli-slo/k8s`
- Destination namespace: `demo1`

## Application is Degraded

```bash
kubectl get pods -n demo1 -l app=orders-api
kubectl describe deployment/orders-api -n demo1
kubectl get events -n demo1 --sort-by=.metadata.creationTimestamp
kubectl logs -n demo1 deploy/orders-api --tail=100
```

Argo CD reports the deployment condition; Kubernetes events and container logs explain why it is unhealthy.

## The UI does not open

```bash
kubectl get svc -n argocd argocd-server
kubectl port-forward -n argocd svc/argocd-server 8080:443
```

Use `https://localhost:8080`, not HTTP. The local installation uses a self-signed certificate.

## Verify self-healing

```bash
kubectl scale deployment/orders-api -n demo1 --replicas=1
kubectl get deployment/orders-api -n demo1 -w
kubectl get application -n argocd orders-api-gitops
```

Expected result: Argo CD reconciles the deployment back to the Git value of two replicas. If it does not, verify `spec.syncPolicy.automated.selfHeal` is `true` in the Application.
