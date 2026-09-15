# Day 11: CI Quality Gates

## Goal

Validate repository changes before they reach `main`, which is the branch Argo CD watches. GitHub Actions verifies repository inputs; Argo CD remains the only deployment controller.

```text
Developer change
      |
      v
GitHub Actions: validate only
  YAML + Python + Bash + kubectl client dry-run
      |
      v
main branch
      |
      v
Argo CD reconciles approved Git state
      |
      v
Kind cluster
```

## What the workflow checks

| Gate | Why it matters |
|---|---|
| YAML structure | Catches malformed Kubernetes, Prometheus, Grafana, and Argo CD YAML before merge. |
| Kubernetes object fields | Ensures lab manifest documents include `apiVersion` and `kind`. |
| Python compilation | Catches syntax errors in the FastAPI service and incident copilot. |
| Bash syntax | Catches syntax errors in the guarded remediation tool. |
| `kubectl --dry-run=client` | Validates the core built-in Kubernetes manifests without a cluster connection. |

The workflow has read-only GitHub permission and no kubeconfig, API key, secret, or deployment credential.

## Files

- [GitHub Actions workflow](../../.github/workflows/ci-quality-gates.yaml)
- [YAML validator](scripts/validate_yaml.py)
- [Local verification script](scripts/verify.sh)

## 1. Install the local validation dependency

From this directory:

```bash
python3 -m venv .venv
.venv/bin/pip install -r config/requirements-ci.txt
```

## 2. Run the local equivalent of CI

```bash
.venv/bin/python scripts/validate_yaml.py

PATH="$(pwd)/.venv/bin:$PATH" ./scripts/verify.sh
```

Expected ending:

```text
All Day 11 local quality gates passed. No cluster resource was changed.
```

The script uses `kubectl apply --dry-run=client`, which prepares objects locally but does not send a create/update request to Kubernetes.

## 3. Publish and inspect GitHub Actions

After this lab is committed and pushed, open the repository **Actions** tab and select **CI quality gates**. The workflow runs on:

- every push to `main`
- every pull request targeting `main`
- manual runs through **Run workflow**

Each green check demonstrates that the source passed its quality gates before Argo CD could observe the new `main` revision.

## 4. Practice a failing gate safely

Do not commit an invalid test. Instead, make a temporary local copy:

```bash
cp ../../day-04-application-sli-slo/k8s/10-orders-api.yaml /tmp/orders-api-invalid.yaml
printf '\ninvalid: [not closed\n' >> /tmp/orders-api-invalid.yaml

.venv/bin/python scripts/validate_yaml.py /tmp/orders-api-invalid.yaml
```

The temporary file is outside the repository, so this safely demonstrates a failed YAML gate without creating an invalid Git change.

## Safety boundary

- CI validates; it does not deploy.
- Argo CD deploys only the desired manifests from Git.
- Do not add `KUBECONFIG`, cluster tokens, or cloud credentials to GitHub Actions for this lab.
- Do not weaken validation to make a failing change pass; fix the source instead.
