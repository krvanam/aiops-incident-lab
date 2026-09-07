# Runbook: NGINX Pod Restart Alert

## Alert meaning

`Demo1NginxPodRestarted` means an NGINX container in namespace `demo1` restarted at least once during the previous five minutes and the condition persisted for one minute.

This lab alert has severity `warning`. In production, tune the threshold and routing based on user impact, replica count, and the service SLO.

## Initial triage

```bash
kubectl get pods -n demo1
kubectl get deployment nginx-demo1 -n demo1
kubectl get events -n demo1 --sort-by=.metadata.creationTimestamp
```

Identify the affected pod from the alert labels, then collect its termination state and previous logs.

```bash
POD_NAME=<pod-name-from-alert>

kubectl get pod -n demo1 "$POD_NAME" \
  -o jsonpath='Reason: {.status.containerStatuses[0].lastState.terminated.reason}{"\n"}Exit code: {.status.containerStatuses[0].lastState.terminated.exitCode}{"\n"}Started: {.status.containerStatuses[0].lastState.terminated.startedAt}{"\n"}Finished: {.status.containerStatuses[0].lastState.terminated.finishedAt}{"\n"}'

kubectl logs -n demo1 "$POD_NAME" --previous --timestamps
```

## Prometheus investigation

Total restart counter:

```promql
sum by (pod, container) (
  kube_pod_container_status_restarts_total{namespace="demo1"}
)
```

Restarts during the last five minutes:

```promql
sum by (pod, container) (
  increase(kube_pod_container_status_restarts_total{namespace="demo1"}[5m])
)
```

## Decision guide

| Evidence | Likely cause | Response |
|---|---|---|
| `OOMKilled` or exit `137` | Memory limit exceeded or kernel kill | Compare memory usage with limits; fix the leak or increase the justified limit. |
| Exit `143` | `SIGTERM` | Check rollout, scale-down, node event, or a manual action. |
| `Completed`, exit `0` | Graceful process exit | Check scheduled shutdown or application lifecycle behaviour. |
| `Error` | Application/configuration failure | Read previous logs and validate image, configuration, dependencies, and probes. |
| Multiple pods restart together | Shared dependency or cluster issue | Check deployment events, node state, DNS, storage, and recent releases. |

## Resolution and follow-up

1. Confirm all desired replicas are ready: `kubectl get deployment nginx-demo1 -n demo1`.
2. Confirm restart growth has stopped in Prometheus.
3. Record the root cause, user impact, mitigation, and permanent corrective action.
4. Tune the alert if it creates noise without actionable impact.
