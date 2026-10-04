# AstraDeploy — Implementation Plan

## Goal and delivery shape

Build AstraDeploy as an original, responsive MLOps resource-provisioning application, not a static dashboard. Prioritize one traceable, usable workflow—from workload registration and context analysis through three resource recommendations, policy/budget review, approval, a clearly labeled demo provisioning/deployment run, monitoring/optimization, reporting, and audit history—then connect the surrounding product modules to the same persisted entities.

All 15 requested navigation destinations will be dedicated pages with meaningful controls and empty/loading/error/success states: Overview, AI Resource Advisor, Workload Analysis, Cloud Resource Optimizer, Deployment Center, ML Pipeline, Model Registry, Experiment Tracking, Resource Monitoring, Cost Intelligence, Infrastructure, Alerts and Notifications, Reports, Team and Access, and Settings. The first delivered version will favor coherent, working demo-mode flows and safe integration boundaries over claiming unavailable production integrations.

## Implementation approach

1. **Foundation and design system**
   - Use the initialized AstraDeploy Webdev project at `/home/ubuntu/astradeploy` (currently empty apart from Git metadata; configured preview port is 3000). Inspect the project’s current stored Webdev configuration before implementation; retain its server and database capabilities.
   - Build a React + TypeScript + Vite frontend, React Router page routes, Tailwind styling, reusable accessible controls and Recharts visualizations.
   - Build a Python FastAPI REST backend with Pydantic validation, SQLAlchemy persistence, versioned API routes, OpenAPI documentation and modular domain services. Serve the compiled frontend and API from the configured web runtime on port 3000; use environment configuration, never embedded credentials.
   - Use the platform-managed SQLAlchemy-compatible MySQL database for this Webdev deployment. Keep the schema and models portable to PostgreSQL through SQLAlchemy and a configurable `DATABASE_URL`; note this platform’s managed database is MySQL-compatible rather than PostgreSQL. Use migrations and deterministic, non-destructive demo seeding.
   - Use Manus OAuth for account identity (the platform’s supported default), with application-side organization membership and role authorization. Do not invent users or silently substitute insecure development authentication. Email verification/password reset are identity-provider responsibilities in this configuration; a future explicitly selected identity provider can supply those flows.

2. **Core domain and connected workflow**
   - Create organization/project/workload records and validated workload input for task/framework, dataset/training scale, CPU/memory/GPU/storage, latency/traffic/scaling, provider preference, budget and availability.
   - Implement a reproducible, deterministic recommendation service combining rules, workload profiles, constraint checks and documented estimate assumptions. Return cost-optimized, balanced and performance-optimized candidates with capacity, estimate, trade-offs, rationale, evidence/confidence, source and rule version. Do not present estimates as guarantees or claim an unevaluated predictive model.
   - Persist workload analyses, recommendations, policy/budget results, approval events, provisioning/deployment state transitions, monitoring samples, optimization decisions, reports and audit events. Enforce tenant scoping and role checks on backend endpoints.
   - In demo mode, create sample records and a simulated, auditable preview/apply lifecycle explicitly marked **Demo / simulated**. Do not describe simulated resources, prices, deployments, metrics, or savings as live. Show a plan preview and require confirmation in the UI before the demo state transition.

3. **MLOps and operations modules**
   - Add pipeline templates and runs with visible, persisted stages (ingest, validate, preprocess, features, train, evaluate, register, deploy, monitor), statuses, logs and retryable demo transitions; do not execute arbitrary user code.
   - Add model/version metadata and lifecycle actions, experiment runs/parameters/metrics, deployment environments/status/history, optimizer recommendations and outcome recording, cost/budget views, alerts/acknowledgment, reports and team/access/settings views.
   - Add dedicated integration states and adapter interfaces for AWS, Azure, GCP, Terraform, Kubernetes, MLflow, Prometheus/Grafana and billing. Enable real data/actions only after an integration is configured and valid permissions exist. Provide one tenant-scoped `/api/v1/workspace` snapshot plus an authenticated `/api/v1/workspace/events` Server-Sent Events feed. Audited mutations atomically advance the organization revision; connected clients refresh when it changes (typically within about two seconds), show Connected/Reconnecting state, and retain a 60-second fallback. No provider/billing/monitoring connector is currently enabled; provider telemetry remains demo-only, and no actual cloud provisioning is authorized by this plan.
   - Keep unavailable live features honest: no fabricated live telemetry or billing; show setup/connect states and use labeled demo seed data. Gate expensive, destructive and production-impacting live actions behind policy checks and explicit approval.

4. **Security, deployment and maintainability**
   - Use Manus OAuth and app roles (Admin, ML/DevOps Engineer, Data Scientist/Developer, Viewer), organization-scoped data access, input validation, upload type/size checks, safe errors, audit records and secret-free logs/responses.
   - Keep provider integrations behind independent adapters with least-privilege assumptions; never run user-supplied shell/code. Generate/export Terraform/Kubernetes artifacts or previews in demo mode without applying them to real accounts.
   - Include Docker/Docker Compose and environment examples for local demo operation, database migrations/seeds, tests, setup/API/deployment documentation, and modular schemas/services/adapters. Treat cloud apply/teardown as unavailable until credentials, permission checks and explicit approval are in place.

## Project structure

- `frontend/` — Vite React/TypeScript app, route-level pages, shared navigation, dark high-contrast design system, charts, forms, API client and accessible feedback states.
- `backend/app/api/routes.py` — versioned FastAPI routes for auth/context, the consolidated tenant-scoped workspace snapshot, projects, workloads/analysis, recommendations, provisioning previews, operational records, team/access, settings, audit and report export.
- `backend/app/core/` — settings, database/session, OAuth/session integration, tenant/role authorization, validation, logging and error handling.
- `backend/app/models/entities.py` and `backend/app/schemas.py` — SQLAlchemy tenant-scoped entities and Pydantic request/response contracts.
- `backend/app/services/` — transparent workload analysis/recommendation rules and organization-scoped demo seeding; record state transitions live in the API service layer.
- `backend/app/adapters/` — provider, Terraform, Kubernetes, MLflow and metrics interfaces with explicit unavailable/configured/demo states.
- `backend/migrations/` — Alembic environment and generated initial tenant-scoped schema; labeled fixtures live in `backend/app/services/seed.py`.
- `infra/` — safe reusable Terraform/Kubernetes examples and preview artifacts; no credentials.
- `tests/test_services.py` and `tests/test_api.py` — recommendation/service, authentication claim, provider safety, API, authorization/tenant isolation, budget and report regression tests.
- Root project configuration and docs — Dockerfiles/Compose, `.env.example`, route manifest, setup, API, testing, demo-mode, integration and deployment documentation.

## Design direction

- **Design movement:** Editorial cloud control room: precise data-instrument design with restrained industrial-console cues, avoiding a generic analytics template.
- **Core principles:** (1) Decision context before raw metrics. (2) Actual, estimated and simulated values are unmistakably distinct. (3) Dense operational information stays legible through hierarchy and spacing. (4) Consequential actions expose their policy, cost and approval state.
- **Color philosophy:** Deep ink/navy and layered slate surfaces keep the whole operations workspace focused and low-glare; high-contrast near-white text ensures legibility; vivid Astra teal marks decisions and healthy states; amber and rose signal budget/policy warnings and failures. Charts use a restrained, color-blind-conscious palette.
- **Layout paradigm:** Persistent dark sidebar and top context bar frame a page-specific dark workspace. Use a left-to-right decision flow and contextual detail rails rather than a single mega-dashboard; tables and charts get full-width space when useful.
- **Signature elements:** A small angular “A” built from two converging provisioning paths; a contextual “decision rail” showing requirements → constraints → recommendation; compact status/evidence chips that differentiate demo, estimate, live, and approval states.
- **Interaction philosophy:** Progressive disclosure; editable inputs yield explainable alternatives; previews precede state changes; destructive or costly operations require clear, explicit confirmation. Every visible control has a defined action.
- **Animation:** Short, subtle transitions (roughly 140–220 ms) for navigation, recommendation comparison and status changes; skeletons for loading; no looping decorative motion; respect reduced-motion preferences.
- **Typography:** Inter/DM Sans for interface and long-form labels; JetBrains Mono for IDs, resource specs and code-like values. Use a readable scale (supporting copy at least 11–12 px, core body 14–16 px, headings 18–30 px) with tabular numerals for costs and metrics.
- **Brand essence:** “Context-aware infrastructure decisions for teams shipping machine learning.” Personality: **precise, calm, resourceful**.
- **Brand voice:** Direct, evidence-led, candid about uncertainty. Examples: “Right-size the workload, not the guess.” “Estimated from your workload profile · demo pricing, not a live quote.”
- **Wordmark & logo:** Custom AstraDeploy wordmark paired with a geometric A-mark formed from two converging resource paths, with a small node at the selected configuration.
- **Signature brand color:** Astra teal, used selectively for actionable recommendations and selected navigation.

## Assumptions and open risks

- The supplied attachment is the authoritative product scope. The current managed project is empty and its preview is configured for port 3000.
- AstraDeploy initialization enabled server and managed database. The managed database is MySQL-compatible; requested PostgreSQL support will be portable via SQLAlchemy/configurable `DATABASE_URL`, but PostgreSQL is not the managed default here.
- Manus OAuth is the default supported identity flow; native email/password plus verification/reset is not assumed without a separate identity-provider choice.
- AWS, Azure, GCP, Grafana and other external integrations are not currently enabled/configured. Live provisioning, billing and monitoring therefore remain gated integration capabilities; demo behavior must be explicitly labeled.
- The broad production-oriented scope spans multiple systems. Prioritize a demonstrably connected end-to-end application and implement each requested module to the extent supported by available services; report any unconfigured provider-dependent capability accurately rather than simulate it as live.
- No external cloud resource creation, teardown, broad publishing or production-impacting operation is included without configured credentials and any required explicit user approval.
