#!/usr/bin/env python3
"""Read-only incident evidence collector for the local Orders API lab.

The program never runs kubectl mutation commands. It gathers facts from
Prometheus and Kubernetes, derives limited evidence-based hypotheses, and
writes a Markdown incident brief suitable for human or LLM review.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import textwrap
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


NAMESPACE = "demo1"
DEPLOYMENT = "orders-api"
ARGOCD_NAMESPACE = "argocd"
ARGOCD_APPLICATION = "orders-api-gitops"
ERROR_THRESHOLD_PERCENT = 5.0
P95_THRESHOLD_SECONDS = 0.5


def run_kubectl(*args: str) -> tuple[str | None, str | None]:
    """Run a fixed, read-only kubectl command and return stdout or an error."""
    command = ["kubectl", *args]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"{' '.join(command)}: {exc}"

    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "unknown kubectl error"
        return None, f"{' '.join(command)}: {message}"
    return completed.stdout.strip(), None


def kubectl_json(*args: str) -> tuple[dict[str, Any] | None, str | None]:
    output, error = run_kubectl(*args, "-o", "json")
    if error:
        return None, error
    try:
        return json.loads(output or "{}"), None
    except json.JSONDecodeError as exc:
        return None, f"kubectl JSON decode error: {exc}"


def prometheus_query(base_url: str, query: str) -> tuple[float | None, str | None]:
    """Execute an instant Prometheus query and return a scalar result."""
    endpoint = f"{base_url.rstrip('/')}/api/v1/query?{urllib.parse.urlencode({'query': query})}"
    try:
        with urllib.request.urlopen(endpoint, timeout=15) as response:
            payload = json.load(response)
    except Exception as exc:  # noqa: BLE001 - report connectivity failures as evidence gaps.
        return None, f"Prometheus query failed: {exc}"

    results = payload.get("data", {}).get("result", [])
    if not results:
        return None, "Prometheus returned no series."
    try:
        return float(results[0]["value"][1]), None
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        return None, f"Prometheus response could not be parsed: {exc}"


def fmt_number(value: float | None, suffix: str = "") -> str:
    return "unavailable" if value is None else f"{value:.2f}{suffix}"


def pod_facts(pods: dict[str, Any] | None) -> list[str]:
    if not pods:
        return ["Pod data unavailable."]

    facts: list[str] = []
    for item in pods.get("items", []):
        name = item.get("metadata", {}).get("name", "unknown")
        phase = item.get("status", {}).get("phase", "Unknown")
        statuses = item.get("status", {}).get("containerStatuses", [])
        ready = all(status.get("ready", False) for status in statuses) if statuses else False
        restarts = sum(int(status.get("restartCount", 0)) for status in statuses)
        facts.append(f"`{name}`: phase={phase}, ready={ready}, restarts={restarts}")
    return facts or ["No Orders API pods were returned."]


def infer(error_rate: float | None, p95: float | None, logs: str | None) -> tuple[list[str], str]:
    """Create bounded inferences; every item remains explicitly non-factual."""
    inferences: list[str] = []
    recommendation: str

    if logs and "fail=true" in logs:
        inferences.append(
            "Controlled `?fail=true` traffic appears in recent logs; this can explain elevated 5xx metrics."
        )
        recommendation = "Stop the synthetic failure traffic and allow the alert window to age out. Do not restart solely for this test signal."
    elif error_rate is not None and error_rate > ERROR_THRESHOLD_PERCENT and p95 is not None and p95 > P95_THRESHOLD_SECONDS:
        inferences.append("Both error rate and p95 latency exceed the local SLO thresholds; this suggests broad user-facing degradation.")
        recommendation = "Follow the Day 9 incident runbook: assess dependency health, recent Git changes, resource pressure, and customer impact before any mitigation."
    elif error_rate is not None and error_rate > ERROR_THRESHOLD_PERCENT:
        inferences.append("Error rate exceeds the local SLO threshold while latency is not proven high; this may be an application or dependency failure.")
        recommendation = "Inspect request-specific application logs and dependency evidence. A restart needs a documented transient-failure hypothesis and human approval."
    elif p95 is not None and p95 > P95_THRESHOLD_SECONDS:
        inferences.append("p95 latency exceeds the local SLO threshold while error rate is not proven high; this may indicate a slow dependency, saturation, or injected delay.")
        recommendation = "Check traffic shape, resources, downstream latency, and whether `delay_ms` test traffic is active. Do not restart without evidence it is restart-safe."
    elif error_rate is None and p95 is None:
        inferences.append("No current Prometheus SLI values were available, so incident classification is incomplete.")
        recommendation = "Restore Prometheus connectivity or generate sufficient application traffic, then rerun the copilot."
    else:
        inferences.append("Current collected SLI values do not exceed the local Day 5 alert thresholds.")
        recommendation = "No remediation is recommended. Continue observation and investigate only if an alert is active or user impact is reported."

    return inferences, recommendation


def markdown_report(
    generated_at: str,
    error_rate: float | None,
    error_error: str | None,
    p95: float | None,
    p95_error: str | None,
    request_rate: float | None,
    request_error: str | None,
    deployment: dict[str, Any] | None,
    deployment_error: str | None,
    pods: dict[str, Any] | None,
    pods_error: str | None,
    argocd_status: str | None,
    argocd_error: str | None,
    events: str | None,
    events_error: str | None,
    logs: str | None,
    logs_error: str | None,
) -> str:
    available = deployment.get("status", {}).get("availableReplicas", 0) if deployment else "unavailable"
    desired = deployment.get("spec", {}).get("replicas", "unavailable") if deployment else "unavailable"
    inferences, recommendation = infer(error_rate, p95, logs)

    evidence_gaps = [
        error for error in (error_error, p95_error, request_error, deployment_error, pods_error, argocd_error, events_error, logs_error) if error
    ]
    event_excerpt = events or "No event output available."
    log_excerpt = logs or "No log output available."

    return f"""# Orders API Incident Intelligence Brief

Generated: `{generated_at}`<br>
Scope: `{NAMESPACE}/{DEPLOYMENT}`<br>
Mode: **read-only evidence collection**

## Safety boundary

This report does not execute remediation and is not a root-cause determination. Any change requires a human incident owner and the guarded Day 9 workflow.

## Observed facts

### SLI values from Prometheus (five-minute window)

| Signal | Value | Local alert threshold |
|---|---:|---:|
| 5xx error rate | {fmt_number(error_rate, '%')} | > {ERROR_THRESHOLD_PERCENT:.0f}% |
| p95 latency | {fmt_number(p95 * 1000 if p95 is not None else None, ' ms')} | > {P95_THRESHOLD_SECONDS * 1000:.0f} ms |
| Request rate | {fmt_number(request_rate, ' req/s')} | Informational |

### Kubernetes and GitOps state

- Deployment desired/available replicas: `{desired}/{available}`
- Argo CD Application: `{argocd_status or 'unavailable'}`
- Pod observations:
{chr(10).join(f'- {fact}' for fact in pod_facts(pods))}

### Recent Kubernetes events

```text
{event_excerpt}
```

### Recent application logs

```text
{log_excerpt}
```

## Evidence gaps

{chr(10).join(f'- {gap}' for gap in evidence_gaps) if evidence_gaps else '- None reported by the collector.'}

## Evidence-based inferences (not facts)

{chr(10).join(f'- {item}' for item in inferences)}

## Recommended next step

{recommendation}

Relevant runbook: `labs/day-09-incident-runbooks-remediation/runbooks/orders-api-incident.md`

## Human approval boundary

If a controlled restart is justified, an incident owner must explicitly run the Day 9 command:

```bash
./scripts/orders-api-guarded-remediation.sh --apply
```

The copilot must not run this command or any other mutating Kubernetes command.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a read-only Orders API incident evidence brief.")
    parser.add_argument("--prometheus-url", default="http://localhost:9090", help="Prometheus base URL (default: http://localhost:9090)")
    parser.add_argument("--output", type=Path, help="Write the Markdown report to this local path; otherwise print it.")
    args = parser.parse_args()

    queries = {
        "error_rate": "100 * sum(rate(demo_api_http_requests_total{namespace=\"demo1\",status_code=~\"5..\"}[5m])) / sum(rate(demo_api_http_requests_total{namespace=\"demo1\"}[5m]))",
        "p95": "histogram_quantile(0.95, sum by (le) (rate(demo_api_http_request_duration_seconds_bucket{namespace=\"demo1\"}[5m])))",
        "request_rate": "sum(rate(demo_api_http_requests_total{namespace=\"demo1\"}[5m]))",
    }
    error_rate, error_error = prometheus_query(args.prometheus_url, queries["error_rate"])
    p95, p95_error = prometheus_query(args.prometheus_url, queries["p95"])
    request_rate, request_error = prometheus_query(args.prometheus_url, queries["request_rate"])

    deployment, deployment_error = kubectl_json("get", "deployment", DEPLOYMENT, "-n", NAMESPACE)
    pods, pods_error = kubectl_json("get", "pods", "-n", NAMESPACE, "-l", "app=orders-api")
    argocd_status, argocd_error = run_kubectl(
        "get", "application", ARGOCD_APPLICATION, "-n", ARGOCD_NAMESPACE,
        "-o", "jsonpath={.status.sync.status}{\" / \"}{.status.health.status}",
    )
    events, events_error = run_kubectl("get", "events", "-n", NAMESPACE, "--sort-by=.metadata.creationTimestamp")
    logs, logs_error = run_kubectl("logs", "-n", NAMESPACE, f"deployment/{DEPLOYMENT}", "--tail=30", "--prefix=true")

    report = markdown_report(
        dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        error_rate, error_error, p95, p95_error, request_rate, request_error,
        deployment, deployment_error, pods, pods_error, argocd_status, argocd_error,
        events, events_error, logs, logs_error,
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote read-only incident brief to {args.output}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
