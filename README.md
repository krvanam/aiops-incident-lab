# AIOps Incident Intelligence Lab

A hands-on Kubernetes, observability, and AIOps portfolio project.

## Learning labs

Each day is self-contained: its guide, manifests, runbooks, and later supporting code live together.

| Day | Lab | Outcome |
|---|---|---|
| 1 | [Kubernetes foundations](labs/day-01-kubernetes-foundations/) | Run NGINX on Kind, inspect resources, troubleshoot image pulls, and expose it with a Service. |
| 2 | [Prometheus and Grafana](labs/day-02-prometheus-grafana/) | Observe cluster and workload metrics, query pod restarts, and investigate a controlled container restart. |
| 3 | [Alerting and SLOs](labs/day-03-alerting-and-slos/) | Deploy, trigger, and investigate a Prometheus pod-restart alert with an operational runbook. |
| 4 | [Application SLIs and SLOs](labs/day-04-application-sli-slo/) | Build an instrumented FastAPI service, scrape application metrics, and calculate availability and latency indicators. |
| 5 | [SLO-based alerting](labs/day-05-slo-alerting/) | Alert on user-facing error rate and p95 latency, then investigate the alerts through a runbook. |
| 6 | [Alertmanager routing](labs/day-06-alertmanager-routing/) | Group related SLO alerts by owning team and service, then route them to a training receiver. |
| 7 | [Grafana dashboard as code](labs/day-07-grafana-dashboard-as-code/) | Provision an Orders API incident dashboard from Git with SLI, SLO, and alert-state panels. |
| 8 | [GitOps with Argo CD](labs/day-08-gitops-argocd/) | Continuously reconcile the Orders API from this Git repository, with automated self-healing and no automatic pruning. |
| 9 | [Incident runbooks and guarded remediation](labs/day-09-incident-runbooks-remediation/) | Triage an Orders API SLO incident, collect before-and-after evidence, and perform only an explicitly approved rollout restart. |
| 10 | [AIOps Incident Intelligence Copilot](labs/day-10-aiops-incident-copilot/) | Build an evidence-backed, read-only incident brief from Prometheus, Kubernetes, Argo CD, and runbook context. |
| 11 | [CI quality gates](labs/day-11-ci-quality-gates/) | Validate YAML, Python, Bash, and core Kubernetes manifests before Git changes reach the Argo CD deployment source. |
| 12 | [OpenTelemetry tracing](labs/day-12-opentelemetry-tracing/) | Trace Orders API requests through a local OpenTelemetry Collector and Tempo, then investigate them in Grafana. |

## Day 1 architecture

Day 1 establishes a local Kind cluster and deploys NGINX through a Kubernetes Service.

```text
Colima / Docker
       |
       v
Kind cluster: aiops-lab
       |
       +-- Namespace: demo1
       |      +-- Deployment: nginx-demo1
       |      +-- Service: nginx-demo1-svc (NodePort)
       |      +-- ConfigMap: nginx-demo1-html
       |
       +-- Namespace: monitoring (used on Day 2)
```

## Prerequisites

- Docker engine running through Colima.
- Kind, Helm, Git, and the standalone `kubectl` client installed.
- The Minikube `kubectl` alias removed or disabled.

## Connect to the local cluster

```bash
export KUBECONFIG="$HOME/.kube/aiops-lab-kind.yaml"
kubectl config current-context
kubectl get nodes
```

Expected context: `kind-aiops-lab`.

## Deploy Day 1 application

```bash
cd labs/day-01-kubernetes-foundations
kubectl apply -f k8s/
kubectl get all -n demo1
kubectl get endpointslice -n demo1 \
  -l kubernetes.io/service-name=nginx-demo1-svc
```

Access NGINX locally:

```bash
kubectl port-forward -n demo1 svc/nginx-demo1-svc 8080:80
```

Open `http://localhost:8080` or run `curl http://localhost:8080` from another terminal.

## Safety

This project is a local learning lab. Do not commit passwords, API tokens, customer data, kubeconfig files, or cloud credentials.
