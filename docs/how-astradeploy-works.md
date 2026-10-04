# How AstraDeploy Works

## In one sentence

AstraDeploy is an organization-scoped workspace for describing machine-learning workloads, comparing explainable resource plans, and keeping related project, model, pipeline, deployment-draft, cost-policy, and report records together. **This build is a planning and tracking demo—not a live cloud-provisioning service.**

## Who uses it

- **Organization Admin:** oversees members and roles, reviews settings and integration status, and checks organization-wide audit activity. Role changes are enforced by the API and recorded in the audit trail. Connecting cloud credentials or enabling live provisioning is not available through the current demo UI.
- **ML Engineer / DevOps Engineer:** describes training or inference workloads, inspects resource requirements, compares plan trade-offs, checks a declared budget, and creates a review-only infrastructure preview. The user can also track deployment drafts and demo operational records.
- **Data Scientist / Developer:** organizes work into projects, registers workload requirements, records experiment and model metadata, and reviews pipeline and report records.
- **Viewer:** reviews organization data without write access.

## Typical workflow

1. **Sign in.** Use the configured Manus identity flow. The workspace is scoped to the authenticated organization; access rules are checked by the backend, not just hidden in the UI.
2. **Review Overview.** See organization workloads and application records. AstraDeploy streams its own saved application changes to open sessions, usually within about **two seconds**, and shows whether the event stream is connected or reconnecting. A 60-second refresh is retained as a safety net. This is not a live feed from a cloud account.
3. **Create or select a project.** Keep related workloads and records together within the organization.
4. **Register a workload.** Enter its name, task type, framework, dataset size, training samples and duration, CPU, memory, GPU, storage, latency target, inference request rate, provider preference, availability target, and optional run budget.
5. **Analyze and compare.** AstraDeploy applies transparent workload rules and returns cost-optimized, balanced, and performance-optimized profiles. Compare the suggested CPU/memory/GPU/storage, estimated runtime and illustrative cost, budget fit, rationale, assumptions, and risks. Estimates are based on the entered requirements and a demo rate card; they are not provider quotes or measured performance predictions.
6. **Select a profile and preview.** The infrastructure preview records a sequence of review steps, but **does not run Terraform, apply Kubernetes manifests, create a cloud resource, or incur cloud charges**. Its status explicitly reports that no real resources were created.
7. **Track related work.** Use dedicated pages to manage demo records for pipelines, model versions, experiments, deployment drafts, optimization suggestions, monitoring samples, and alerts. These actions update AstraDeploy's application records; they do not run a model-training job or deploy a live endpoint.
8. **Review and export.** Create report snapshots, inspect audit activity, and export the workload inventory as CSV or JSON.

## Example: planning a vision-training job

An ML engineer starts a project for a defect classifier and registers a PyTorch computer-vision workload. They enter the dataset and training size, expected run time, required memory and GPU count, storage, and a per-run budget. AstraDeploy records the workload, explains its rule-based resource fit, and presents three alternatives with assumptions and estimated cost. The engineer can select a budget-compatible profile and open a simulated plan preview for review. They can then record experiment, model, or deployment-draft metadata and export a report. **The GPU and other cloud resources are not actually created by this workflow.**

## What is live in this build—and what is not

| Capability | Current behavior |
| --- | --- |
| Authentication and organization access | Manus OAuth/session support; tenant-scoped API access and role checks. |
| Application data | Saved through AstraDeploy's configured database; audited changes advance a tenant-scoped revision and an authenticated Server-Sent Events stream prompts open sessions to refresh (typically within about two seconds), with a 60-second fallback. |
| Workload analysis | Runs deterministic, documented rules on user-entered requirements; it is not a trained predictive model. |
| Recommendations and budget checks | Three illustrative resource profiles and a check against the budget the user entered. Cost numbers are demo estimates, not current provider pricing. |
| Plan preview | Review-only record; no provider resource changes occur. |
| Dashboards, monitoring and cost pages | Contain clearly labeled sample/demo metrics and estimates until real sources are connected. |
| Pipeline, model, experiment and deployment pages | Track demo metadata and simulated states; they do not execute training, pipeline jobs, or live deployments. |
| Reports | Saved report snapshots; workload inventory export is available in CSV and JSON. |
| AWS, Azure, Google Cloud, billing, Prometheus/Grafana, MLflow | **Not connected in this build.** No live provider telemetry, billing, cloud pricing, or deployment actions are available. |

## When AstraDeploy is useful now

Use this build to collect ML workload requirements, compare assumptions consistently, discuss resource trade-offs and budgets, organize MLOps metadata, review a non-mutating infrastructure plan, and demonstrate the intended workflow to a team. It is useful for planning and coordination without requiring cloud credentials.

Do **not** use this build as proof that a cloud resource exists, as a live cost or capacity monitor, as a current provider price quote, or as a production deployment/auto-scaling system. Before real cloud operations can be used, the product needs authorized provider integrations, live pricing/metrics sources, working infrastructure apply/deployment adapters, approval and rollback controls, and production validation. Those integrations and live actions are not enabled here.
