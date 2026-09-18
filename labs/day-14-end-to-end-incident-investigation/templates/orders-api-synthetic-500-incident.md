# Orders API Synthetic 500 Incident Record

> Keep this completed record local. It is an exercise artifact and may include runtime timestamps and trace IDs.

## 1. Incident summary

- Date and time detected:
- Alert / dashboard signal:
- Service and namespace: `orders-api` / `demo1`
- SLO affected: availability
- Customer impact in this lab: controlled synthetic 5xx responses only
- Incident owner:

## 2. Metrics evidence

- Five-minute 5xx percentage:
- Availability SLI observed:
- p95 latency observed:
- Alert state and time:

## 3. Platform and GitOps evidence

- Deployment readiness:
- Pod readiness/restart count:
- Relevant Kubernetes events:
- Argo CD sync and health:

## 4. Log and trace evidence

- Loki query used:
- Matching log timestamp:
- Log status code and route:
- Trace ID (local lab only):
- Tempo trace service, route, and error attributes:

## 5. Decision

- Confirmed cause:
- Why a restart is not appropriate:
- Immediate action: stop synthetic failure traffic
- Approval required for any future remediation: incident owner approval and Day 9 `--apply`

## 6. Outcome

- Traffic stopped at:
- Metric / alert recovery time:
- Remaining uncertainty:
- Follow-up:
