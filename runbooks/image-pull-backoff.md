# Runbook: ImagePullBackOff

## Symptom

A pod remains in `ErrImagePull` or `ImagePullBackOff` instead of starting.

## Investigation

```bash
kubectl get pods -n <namespace>
kubectl describe pod <pod-name> -n <namespace>
kubectl get events -n <namespace> --sort-by=.metadata.creationTimestamp
```

## Common causes

- Misspelled image repository or tag.
- Image does not exist in the registry.
- Missing image-pull secret for a private registry.
- Registry access, DNS, or network failure.

## Evidence from the Day 1 drill

```text
Failed to pull image "nginx:this-image-does-not-exist"
docker.io/library/nginx:this-image-does-not-exist: not found
```

## Mitigation

Correct the image name or tag in the Deployment manifest, then apply it and monitor the rollout:

```bash
kubectl apply -f k8s/20-nginx-deployment.yaml
kubectl rollout status deployment/nginx-demo1 -n demo1
```

## Prevention

- Pin a known valid image tag; avoid `latest` in production.
- Validate manifests in CI before deployment.
- Alert on repeated image-pull failures.

