# AstraDeploy — Delivery TODO

Criteria are transcribed from the approved user specification and plan; statuses stay open until there is implementation evidence. Demo/simulation is never represented as live cloud activity.

## 1. Foundation, identity, tenancy and access — partially delivered
- Create an original production-oriented AstraDeploy MLOps cloud-resource-provisioning web application, not a static dashboard or clone; use established MLOps architecture as inspiration without copying proprietary interface, code or branding.
- Provide signup/login, email verification, forgot-password/password-reset where supported by configured identity, secure session management, role-based access, user profile and organization settings, multi-tenant organization support, audit logs and API-key management. Start Manus OAuth via same-origin POST so the browser provides Origin, preserve the browser-visible callback origin, and bind the callback to a single-use nonce.
- Provide Admin (manage users/organizations; view authorized organization workloads/deployments; configure providers, policies, budgets, platform settings; inspect audit logs), ML Engineer/DevOps Engineer (register workloads, upload/manage models, configure requirements, view recommendations, provision only when authorized, deploy/monitor models, analyze cost/performance), Data Scientist/Developer (create projects, register datasets/models, run analysis, view recommendations, track experiments, request deployments), and read-only Viewer access.
- Enforce authorization on every protected backend operation, not just in navigation; enforce organization isolation and restrict each user to authorized organizational data/resources.
- Include organization profile, users, roles/permissions, cloud-account and integration status, resource/budget policies, workload quotas, audit logs, system configuration, background task status and platform health.

## 2. Application shell and route coverage — partially delivered
- Provide a responsive desktop/tablet/mobile app with persistent dark navy/charcoal sidebar, high-contrast dark slate workspace, subtle gradients, clear typography, accessible contrast, breadcrumbs, search, notifications, user profile, organization selector and cloud-environment selector.
- Each is a separate dedicated page with relevant content, functional controls and loading, empty, error and success states—not sections on one long dashboard: Overview; AI Resource Advisor; Workload Analysis; Cloud Resource Optimizer; Deployment Center; ML Pipeline; Model Registry; Experiment Tracking; Resource Monitoring; Cost Intelligence; Infrastructure; Alerts and Notifications; Reports; Team and Access; Settings.
- Include visual hierarchy, compact information cards, usable tables, interactive charts, contextual tooltips, searchable lists, helpful empty states, validation, confirmation dialogs, skeletons and toasts. Meaningful demo examples are allowed only when explicitly labeled. Every button, form, chart filter, table action and navigation link must have a defined behavior; avoid decorative dead controls.
- Follow-up UI correction: use the dark, high-contrast palette on both sign-in and authenticated screens, increase supporting/body text to readable sizes, and retain responsive mobile layout.

## 3. Overview dashboard — partially delivered
- Show registered workload count, active deployments, running pipelines, current utilization, CPU/memory and GPU when available, estimated and actual spending distinctly, allocation efficiency, under/over-provisioned workloads, optimization opportunities, deployment health, recent activity, active alerts and model performance summaries.
- Provide interactive charts for utilization over time, cost trends, workload/provider distribution, deployment successes/failures and allocated versus consumed resources; include last 24 hours, 7 days, 30 days and custom date filters.
- Use connected backend data when available and visibly label sample/demo data.

## 4. Workload registration and analysis — partially delivered
- Allow manual workload creation; upload/import supported workload configuration files, Dockerfiles and Kubernetes YAML; register ML projects; enter workload metrics; connect supported monitoring sources; select registered workloads.
- Accept workload name, task type, framework, dataset size, training duration and sample count, expected inference requests, latency, CPU, memory, GPU, storage, traffic, scaling, preferred provider, maximum budget and availability.
- Analyze CPU, memory, GPU, storage, network, duration, throughput, latency, peak demand, historical utilization and variability. Generate classification, resource-demand profile, bottlenecks, estimated requirements, performance risks, scaling recommendations and cost implications; visualize utilization curves, profiles and forecasts; compare workloads and save analysis history.
- Support training, inference, batch prediction, preprocessing, computer vision, NLP, deep learning, traditional ML, real-time prediction and large-scale data processing.

## 5. AI Resource Advisor and decision engine — partially delivered
- Use rules, resource profiles and trained ML models only where suitable; do not rely solely on an LLM. Consider workload characteristics, historical utilization, current resource availability, provider, budgets, performance and latency, scaling, pricing, policies, availability and reliability.
- Return provider, VM/compute type, CPU/memory, GPU where required, storage, container configuration, Kubernetes requests/limits, autoscaling, estimated runtime/cost/performance and deployment architecture.
- Return cost-optimized, balanced and performance-optimized alternatives; compare costs, capacity, expected performance and suitability; explain workload factors, rationale and trade-offs; allow compare/select/save/export.
- Every result includes selected configuration, estimated demand/cost/performance where supported, constraint validation, rationale, confidence/evidence level, data source and model/rule version. State assumptions and uncertainty; never guarantee performance or savings.
- Provide reproducible training/validation/test evaluation when ML models are used; compare against rule-based baselines using cost, resource fit and constraint satisfaction; if data or live metrics are unavailable, disclose limitation and use documented rules.

## 6. Provisioning and infrastructure lifecycle — partially delivered
- Provide registration → parameter extraction → context analysis → recommendation → cost/policy validation → required user approval → infrastructure provisioning → deployment → monitoring → continuous optimization; support automatic, approval-based and manual modes.
- Use Terraform and provider APIs for actual provisioning only when valid credentials/permissions and explicit authorization are configured. Provide infrastructure-plan preview first. Show statuses, resource-creation logs, progress, failure handling, retry controls, feasible rollback, teardown and infrastructure history.
- Include registered environments, cloud-account connection, reusable ML templates, plan preview/validation/apply approved plans, provisioning status, deployed resources/configuration/history and destruction of approved resources. Handle Terraform state, secrets, access controls and change auditing safely.
- Apply policy checks, budget limits and explicit authorization before costly or destructive cloud operations. Never expose credentials, private keys or sensitive environment variables in logs/frontend. Never imply a simulation is a real provisioned resource.

## 7. Cloud Resource Optimizer — partially delivered
- Detect over/under-provisioned and idle resources, unused storage, inefficient instance selection, unnecessary GPU, memory/CPU bottlenecks, poor autoscaling and costly configurations.
- Recommend right-sizing, reducing unnecessary CPU/memory, instance changes, autoscaling thresholds, scheduling non-urgent work, lower-cost suitable configurations and shutting down approved idle resources.
- Show current/recommended configurations, estimated costs before/after, expected performance impact, risk and rationale. Allow apply-approved or dismiss; record actual outcome after changes and compare with estimates. Label demo outcomes as simulated.

## 8. Pipelines, registry and experiments — partially delivered
- Support reusable pipeline templates/stages for ingestion, validation, preprocessing, feature engineering, training, evaluation, model registration, deployment and monitoring; pipeline creation/versioning/parameters/scheduling/status/logs/errors/retries/artifacts/visual workflow/history; modular engine for future container/framework executors.
- Register/upload model artifacts where feasible (Pickle, Joblib, ONNX and supported framework formats), associate models with projects/datasets, record frameworks/versions/evaluation, manage lifecycle, compare versions, show lineage and promote approved models.
- Track experiments, hyperparameters, training/evaluation metrics, artifacts, model versions, duration, resource use and associated infrastructure. Integrate MLflow only when configured; keep unified UI.

## 9. Deployment Center — partially delivered
- Support model/container deployment, REST inference endpoints, batch jobs, Kubernetes deployment, version/environment/config management, health checks, autoscaling, rollback, logs and traffic/latency metrics.
- Environments: Development, Testing, Staging, Production. States: Draft, Pending approval, Provisioning, Deploying, Running, Failed, Stopped, Rolling back.
- Generate manifests/infrastructure config from approved recommendations. Summarize model version, resources, provider, endpoint information, status and estimated cost. Never mark success unless a real configured deployment process confirms it.

## 10. Cost and budget intelligence — partially delivered
- Show current and daily/weekly/monthly spending, by provider/project/workload/resource type, deployment cost, expenditure forecast, budget consumption, optimization opportunities; distinguish actual billing, estimate and demo data.
- Support budgets at platform/project/resource levels, cost allocation, threshold configuration and alerts at 50%, 75%, 90%, 100%, anomaly detection, forecasting, comparison among recommendations and cost reports.
- Use actual billing only through connected provider billing APIs. Do not claim current pricing without a reliable source; identify timestamps and assumptions.

## 11. Monitoring, predictive analytics and scaling — partially delivered
- Monitor CPU, memory, GPU, disk, network, request rate, inference latency, throughput, errors, deployment health and pipeline status. Integrate Prometheus/Grafana-compatible metrics only when configured; provide time-series, resource dashboards, history comparison, workload/deployment health, alerts and custom intervals; use streaming where supported.
- When monitoring is disconnected, show setup state rather than fabricated real-time data.
- Forecast resource demand, CPU/memory utilization, workload duration, costs, saturation and unusual consumption using suitable historical data. Show horizon, intervals where supported, evaluation metrics, actual-versus-forecast charts and explanations; use held-out evaluation and state that prediction is not ready if data is insufficient, falling back to transparent rules.
- Support horizontal scaling, vertical recommendations, CPU/memory/request/scheduled/custom threshold policies; show min/max replicas, up/down thresholds, cooldown, scaling history/events and resource/cost impact. Preview, approve and activate policies; integrate Kubernetes HPA/cloud APIs when configured.

## 12. Alerts, notifications and observability — partially delivered
- Support alerts for CPU, memory, GPU, deployment/pipeline failure, cost increase/budget thresholds, model degradation, bottlenecks, provisioning failure and unusual activity.
- Provide severity, history, acknowledgment, resolution, assignment, notification preferences, in-app alerts and email/webhook/custom rules only where configured.

## 13. Multi-cloud, APIs, data and persistence — partially delivered
- Use independent AWS/Azure/GCP adapters and a comparison UI for compute, memory, GPU, storage, pricing, regional availability, suitability, scaling and availability; recommend provider from workload/budget/policy. Use current prices only from reliable connected sources with timestamp/assumptions.
- Provide clean versioned REST APIs/OpenAPI modules for authentication, users/orgs, projects/workloads, analysis, recommendations, provisioning, infrastructure, deployment, pipelines, registry, experiments, monitoring, cost, prediction, autoscaling, alerts, reports and administration; validation, authorization, pagination, consistent response formats/errors and background jobs for long operations.
- Live application updates use one tenant-scoped `GET /api/v1/workspace` snapshot plus an authenticated `GET /api/v1/workspace/events` Server-Sent Events stream. Audited mutations atomically advance an organization revision, connected clients refresh on change (typically within about two seconds), expose Connected/Reconnecting state, and retain a 60-second fallback plus the last good snapshot on transient failure. This covers AstraDeploy app data only; disconnected provider telemetry/billing is never shown as live.
- Normalize persistent entities: users, organizations/members, roles/permissions, projects, workloads/metrics/analyses, recommendations, providers/accounts, infrastructure resources, provisioning jobs, environments/deployments/events, pipelines/stages/runs, models/versions, experiments/runs, monitoring metrics, scaling policies/events, budgets/costs, optimization recommendations, alerts/notifications, reports, audit logs and integration settings. Use primary/foreign keys, indexes, timestamps, tenant links and retention; store large artifacts/files in object storage, not relational rows.

## 14. Reports — partially delivered
- Generate workload analysis, recommendation, optimization, utilization, deployment, pipeline, model performance, infrastructure, predictive analytics and audit reports.
- Filter by date, workload, project, provider and deployment; export PDF, CSV and JSON; include charts, findings, configuration comparisons, timestamps and clear actual/estimated distinctions.

## 15. Security and reliability — partially delivered
- Provide secure password hashing if an email/password provider is explicitly used, role-based authorization, tenant isolation, encrypted secret storage, secure API auth, validation, rate limiting, audit trail, safe file upload, cloud-credential isolation, safe infrastructure execution, error handling, backup approach, logging/observability and configurable retention.
- Use least-privilege cloud permissions, do not execute arbitrary shell code or run untrusted user code without isolation. Require clear approval for costly, destructive or production-impacting operations.

## 16. Roadmap separation — complete
- Keep future multi-cloud intelligent scaling, RL autoscaling (only after reliable simulation and evaluation), controlled federated model marketplace, advanced cost intelligence/workload scheduling and policy-driven zero-touch deployment (only explicitly approved and constrained) modular and clearly identified as implemented versus roadmap.

## 17. Runnable delivery, tests and documentation — partially delivered
- Deliver modular frontend/backend, database models/migrations, ML training/inference modules, infrastructure templates, cloud adapters, Dockerfiles, Docker Compose, Kubernetes manifests where applicable, environment examples, API docs, setup/deployment docs, demo seed data and automated tests.
- Run locally in a clearly documented demo configuration without cloud credentials. Live provisioning requires valid credentials/permissions, explicit setup and appropriate approvals. Use environment variables; never commit secrets.
- Implement unit tests for recommendations; API integration; authentication/authorization; database; frontend components; workload analysis; provisioning adapters; pipeline execution; ML evaluation; end-to-end workflow. Cover invalid workload inputs, missing credentials, budget violations, cloud API failures, failed deployment, unavailable resources and incomplete monitoring. Include sample test data, reproducible commands and documented test environment.
- Keep modules testable and integrated across phases. Provide clear errors, execution logs and status updates. Never claim a model is trained/accurate without real training/evaluation, cloud provisioning when only simulated, or real metrics/costs from hardcoded samples; no essential route/button/form/workflow may be left inert.
