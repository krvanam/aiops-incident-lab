# Orders API Dashboard Runbook

## Purpose

Use the **Orders API — Operations Overview** dashboard as the starting point
for an incident involving the Orders API service.

## Operator workflow

1. Check **Firing Orders API SLO Alerts**. A value of `1` or `2` means the Day
   5 SLO alerts are active.
2. Check **Availability SLI** and **5xx Error Rate** together. A 5xx rate over
   5% explains `OrdersApiHighErrorRate`.
3. Check **p95 Latency** and its trend. A value above `0.5 s` explains
   `OrdersApiHighP95Latency`.
4. Use **Request Rate by Status Code** to distinguish a low-traffic anomaly
   from broad service impact.
5. Use **Container Restarts — Last Hour** to decide whether to investigate a
   Kubernetes workload failure or an application/dependency symptom.
6. Open the Day 5 SLO-breach runbook and the Day 6 Alertmanager group for the
   full incident context.

## What the dashboard does not prove

The dashboard shows symptoms and supporting runtime signals. It does not prove
root cause. Confirm root cause with pod logs, events, deployment history,
dependency checks, and the relevant runbook.

## SLO thresholds used by this lab

| Signal | Target | Day 5 alert threshold |
|---|---:|---:|
| Availability | 99.9% | 5xx rate above 5% for two minutes |
| p95 latency | below 500 ms | p95 above 500 ms for two minutes |
