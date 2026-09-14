# Day 10: AIOps Incident Intelligence Copilot

## Goal

Build a provider-free, evidence-backed incident copilot for the Orders API. It collects live operational facts from Prometheus, Kubernetes, and Argo CD, then produces a Markdown brief that a human—or an approved LLM—can review safely.

```text
Prometheus metrics      Kubernetes state       Argo CD status       Runbook
       |                       |                    |                |
       +-----------------------+--------------------+----------------+
                                       |
                                       v
                        Read-only incident evidence collector
                                       |
                                       v
                   Facts + gaps + bounded inferences + next step
                                       |
                                       v
                   Human decision / Day 9 guarded remediation
```

## Why this is an AIOps copilot, not autonomous remediation

The collector is intentionally deterministic about evidence gathering. It labels all hypotheses as **inferences**, keeps evidence gaps visible, and cannot change the cluster. This gives an LLM high-quality context without giving it authority to remediate.

There are no third-party Python dependencies and no API keys. You can optionally paste the generated brief into Codex with [the evidence review prompt](prompts/evidence-review-prompt.md).

## What it collects

- Five-minute 5xx error rate, p95 latency, and request rate from Prometheus.
- Orders API Deployment and Pod readiness/restart state.
- Recent namespace events and application logs.
- Argo CD `Sync / Health` state.
- Evidence gaps when any source cannot be reached.

## Prerequisites

- Days 4–9 completed.
- Python 3 and `kubectl` installed.
- Prometheus exposed locally in one terminal:

```bash
kubectl port-forward -n monitoring \
  svc/monitoring-kube-prometheus-prometheus 9090:9090
```

## 1. Generate a healthy-state brief

In a second terminal:

```bash
cd /Users/krvanam/AI-Projects/aiops-incident-lab/labs/day-10-aiops-incident-copilot

python3 scripts/incident_copilot.py \
  --output reports/healthy-state.md

sed -n '1,220p' reports/healthy-state.md
```

The report is local and ignored by Git because it can contain logs and runtime information.

## 2. Generate an elevated-error brief

Expose the application in another terminal:

```bash
kubectl port-forward -n demo1 svc/orders-api 8081:80
```

Generate controlled traffic in a separate terminal. Stop it with `Ctrl+C` after collecting evidence:

```bash
while true; do
  curl -s http://localhost:8081/api/orders > /dev/null
  curl -s http://localhost:8081/api/orders > /dev/null
  curl -s -o /dev/null 'http://localhost:8081/api/orders?fail=true'
  sleep 2
done
```

After Prometheus has scraped the traffic, run:

```bash
python3 scripts/incident_copilot.py \
  --output reports/high-error-rate.md

sed -n '1,220p' reports/high-error-rate.md
```

Expected: the copilot reports an elevated 5xx rate and recommends stopping synthetic failure traffic rather than restarting the workload.

## 3. Generate an elevated-latency brief

Instead of failure traffic, use a latency test:

```bash
while true; do
  curl -s 'http://localhost:8081/api/orders?delay_ms=900' > /dev/null
  sleep 2
done
```

Then generate `reports/high-latency.md`. Expected: the copilot identifies p95 above the local threshold and asks you to verify traffic/dependency evidence before considering any mitigation.

## 4. Use Codex as the reasoning layer

Open [the evidence review prompt](prompts/evidence-review-prompt.md), paste it into Codex, then replace the placeholder with the report content. Codex can help interpret the evidence, but the report’s human-approval boundary remains in force.

## Safety boundary

- `incident_copilot.py` has no mutation path and does not call `kubectl apply`, `delete`, `scale`, `rollout restart`, or `exec`.
- It must not be wired directly to Prometheus/Alertmanager for automatic changes.
- Do not commit generated reports, tokens, kubeconfig files, or unredacted production logs.
- The Day 9 script remains the only lab mechanism for a controlled restart, and it still requires `--apply`.

## Portfolio talking point

> Built an evidence-first AIOps incident copilot that correlates Prometheus SLIs, Kubernetes workload state, logs, and GitOps health into an auditable incident brief, with explicit uncertainty and human approval before remediation.
