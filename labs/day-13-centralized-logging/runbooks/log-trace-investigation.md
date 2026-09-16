# Orders API Log and Trace Investigation

Use logs to locate an individual failing request, then follow its trace ID into Tempo.

## First checks

```bash
kubectl get pods -n logs
kubectl logs deployment/alloy-log-collector -n logs --tail=50
kubectl logs deployment/loki -n logs --tail=50
```

## LogQL starting point

In Grafana **Explore**, select **Loki** and run:

```logql
{namespace="demo1", app="orders-api"} |= "event=orders_request"
```

For controlled failures:

```logql
{namespace="demo1", app="orders-api"} |= "status_code=500"
```

Each matching line contains `trace_id=<32 hexadecimal characters>`. Select **View trace** to open the related Tempo trace.

## Interpretation

| Evidence | Meaning | Next action |
| --- | --- | --- |
| `status_code=200` with high `duration_ms` | Slow but successful request | Open the trace; inspect span duration. |
| `status_code=500` | Application-level failure | Open the trace; compare it with a successful request. |
| No log lines | Collection, labels, or Loki query issue | Check Alloy logs, its RBAC, and datasource. |

The lab uses `emptyDir` storage in Loki. Logs are intentionally temporary and disappear if the Loki pod is removed.
