# Alert Routing and Grouping Runbook

## Purpose

Use this runbook when alerts are noisy, arrive separately despite being part of
one incident, or go to the wrong support team.

## Day 6 route

| Matcher | Receiver | Group labels | Intent |
|---|---|---|---|
| `alertname="Watchdog"` | `default-null` | N/A | Ignore the synthetic health-check alert. |
| `team="platform"`, `service="orders-api"` | `platform-training` | `team`, `service` | Treat error-rate and latency symptoms as one Orders API incident. |
| Anything else | `default-null` | `team`, `service` | Safe local default; no external notification. |

`platform-training` deliberately has no Slack, PagerDuty, email, or webhook
configuration. It lets us validate alert grouping without storing credentials.

## Triage workflow

1. Open Alertmanager and identify the group labels: team and service.
2. Expand the group and identify every alert in the incident.
3. Read the Day 5 SLO runbook for error-rate and p95-latency investigation.
4. Decide whether the symptoms share one cause. Do not close one alert merely
   because another alert exists.
5. In production, route the group to the owning team receiver and include the
   applicable runbook URL.

## Key terms

- **Routing:** selects a receiver by alert labels.
- **Grouping:** combines related alerts before notification to reduce noise.
- **`group_wait`:** wait before the first notification so related alerts can
  join the group.
- **`group_interval`:** minimum wait before sending an update for new alerts
  joining an already-notified group.
- **`repeat_interval`:** how often Alertmanager repeats an unresolved alert.
- **Inhibition:** suppresses a lower-severity symptom when a higher-severity
  alert establishes the same underlying issue.

## Production guardrails

- Include `namespace`, `cluster`, and environment in grouping when one receiver
  supports multiple environments.
- Use a team-owned receiver; never send production alerts to a personal token
  or a test webhook.
- Keep a safe default route for unmatched alerts and monitor that route.
- Test routing with a non-production alert before changing paging policy.
