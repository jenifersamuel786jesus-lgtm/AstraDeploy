# AstraDeploy

AstraDeploy is an organization-scoped MLOps resource-planning application. It registers ML workloads, analyzes user-entered requirements, compares explainable rule-based resource plans, checks a declared budget before showing a plan preview, and tracks demo MLOps records through dedicated pages.

## Truthful operating modes

- **Demo data is labeled.** Seeded utilization, cost, deployment and model records are examples, not live telemetry or billing.
- **Recommendation estimates are rules, not a trained ML model or cloud price quote.** The API returns the rule version, rationale, assumptions, evidence level and budget fit. Predictive-model readiness is false because representative historical data is unavailable.
- **Cloud providers, billing, metrics and MLflow are disconnected.** The AWS/Azure/GCP adapter contract checks whether protected environment fields are present but exposes no values and has no live provisioning implementation.
- **Plan preview is non-mutating.** It records `real_resources_created: false`; no Terraform apply, Kubernetes apply, cloud deployment or resource deletion is implemented.
- **Authentication uses Manus OAuth.** It validates Preview's `webdev_app_session` HS256 JWT against `MANUS_JWT_SECRET`, expiry and `MANUS_PROJECT_ID`, and also supports the OAuth code-exchange path. Sign-in starts through a same-origin POST with a same-origin referrer; initiation requires a browser Origin or Referer matching the fixed callback origin. Completion checks the exact saved callback URL against the OAuth state and single-use nonce cookie, so Preview's rewritten callback request headers do not break validation. The frontend deduplicates concurrent code exchanges by OAuth state, and provider errors identify whether token exchange or profile lookup failed. The application session cookie is `SameSite=None; Secure` for HTTPS Preview. Standalone local sign-in needs the Manus OAuth runtime values; no fake development user or password bypass is provided.

## Project structure

- `frontend/src/` — responsive React/TypeScript UI, route views, shared workload form, API client and visual system.
- `backend/app/api/` — versioned FastAPI routes and OpenAPI contracts.
- `backend/app/core/` — database/session/security infrastructure.
- `backend/app/models/` — tenant-scoped SQLAlchemy entities.
- `backend/app/services/` — rule-based workload analysis, explainable recommendations and idempotent demo seeding.
- `backend/app/adapters/` — safe cloud-provider status/plan-preview interfaces; live provisioning is intentionally disabled.
- `backend/migrations/` — Alembic environment and versioned schema revisions.
- `infra/` — review-only Terraform and Kubernetes templates; neither template creates resources when used as supplied.
- `tests/` — API, tenancy, authorization, workload analysis, recommendation and adapter tests.
- `docs/plan.md`, `TODO.md` — approved design/implementation plan and detailed acceptance tracker.
- `docs/how-astradeploy-works.md` — who the workspace is for, how to use it, and which actions remain demo-only.

## Local development

Requirements: Node.js 22, pnpm 11.25.0, and Python 3.11+.

```bash
pnpm install
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt

# Use SQLite for an offline local demo; live cloud credentials are not needed.
export DATABASE_URL='sqlite:///./astradeploy.db'
export ASTRA_LOCAL_HTTP_COOKIES=true
alembic upgrade head

# Terminal 1: API server
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Vite frontend; /api and /manus-routes.json proxy to the API
pnpm dev
```

The app's sign-in page remains logged out until a valid Manus identity is available. Vite localhost URLs are not automatically approved OAuth callback origins; configure the provider's accepted callback policy before attempting standalone OAuth. In the managed HTTPS Preview, the platform supplies identity/runtime values and may inject the validated application session cookie.

To build and serve the production UI/API together on port 3000:

```bash
pnpm build
DATABASE_URL='sqlite:///./astradeploy.db' ASTRA_LOCAL_HTTP_COOKIES=true \
  .venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 3000
```

`docker compose up --build` runs the same local SQLite demo on `http://localhost:3000` with a named data volume. Set `DATABASE_URL` explicitly only if intentionally choosing a compatible external/local database. Do not place provider keys in browser configuration.

## Database and API

- The Webdev project is configured with its managed MySQL-compatible database; startup applies the committed Alembic head non-destructively. The database layer translates the platform's JSON-encoded Node-style TLS URL option into PyMySQL's native SSL configuration without logging connection material.
- `DATABASE_URL` may also point to local SQLite or supported PostgreSQL for standalone development.
- Alembic revision history is under `backend/migrations/`; run `alembic upgrade head` for a deterministic schema migration. Review and back up data before any user-authored destructive schema change.
- FastAPI OpenAPI docs are at `/docs`; JSON schema is `/openapi.json`. Health is `/healthz` and `/api/v1/health`.
- Versioned route groups include identity, projects, workloads, analysis, recommendations, record collections/actions, the workspace snapshot and its authenticated SSE event stream, team/settings, audit and JSON/CSV report exports. Admins can change another in-organization member's role; self-demotion is rejected, a last-admin role cannot be removed, and all role edits are audited. All protected data lookups are scoped to the authenticated organization; API writes enforce role permissions.

## Workspace APIs and data freshness

The authenticated UI loads its organization-scoped dashboard, workloads, records, team, settings, and audit data through one `GET /api/v1/workspace` snapshot. The same-origin `GET /api/v1/workspace/events` Server-Sent Events endpoint sends a tenant-scoped change notice whenever an audited app mutation atomically advances the organization revision. Connected sessions fetch a fresh snapshot on change (typically within about two seconds), show Connected/Reconnecting status, keep the last successful snapshot during transient API errors, and offer manual retry plus a 60-second fallback refresh. This is live AstraDeploy application data—not live cloud telemetry. Provider charts, costs, alerts, and sample workloads remain visibly demo/estimated until an authorized AWS, Azure, or Google Cloud account and its metrics/billing sources are configured.

## Tests and checks

```bash
.venv/bin/pytest -q
pnpm typecheck
pnpm build
.venv/bin/python -m compileall -q backend
```

Tests cover organization isolation, write-role enforcement, project/workload validation, OAuth callback origin and nonce flow, persisted session expiry/logout, dashboard time windows, budget guardrails, non-mutating plan previews, report categories/exports, recommendation assumptions and managed-MySQL TLS URL mapping.

## Future integrations

Multi-cloud Terraform/Kubernetes apply, current cloud price catalogs, production deployment, MLflow, Prometheus/Grafana, trained demand estimation, predictive analytics and automated autoscaling require connected services, reliable source data, evaluation and explicit authorization. These capabilities are **not live in this build**; roadmap concepts are labeled separately in Settings.
