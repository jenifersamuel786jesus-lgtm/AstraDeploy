from __future__ import annotations

import asyncio
import base64
import csv
import io
import json
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import (
    COOKIE_NAME, _hash_token, cookie_secure, create_session, current_context, ensure_user_and_org,
    require_roles, resolve_user,
)
from backend.app.models.entities import (
    AppSession, AuditLog, DemoRecord, Deployment, Membership, Organization, Project,
    Recommendation, User, Workload, WorkloadAnalysis, utcnow,
)
from backend.app.schemas import ActionInput, OAuthStartInput, ProjectInput, RecordCreate, ReportInput, RoleUpdate, WorkloadInput
from backend.app.services.recommendation import analyze_workload, build_recommendations
from backend.app.services.seed import SAMPLE_RECORDS, seed_demo_workspace

router = APIRouter(prefix="/api/v1")
EDITOR_ROLES = {"Admin", "ML/DevOps Engineer", "Data Scientist/Developer"}
OPERATOR_ROLES = {"Admin", "ML/DevOps Engineer"}
RECORD_KINDS = {"pipelines", "models", "experiments", "alerts", "budgets", "deployments", "costs", "optimizations", "infrastructure", "metrics", "activity", "integrations", "provisioning", "notifications", "reports", "scaling"}


def get_context(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    return current_context(request, db)


def _audit(db: Session, ctx: dict[str, Any], action: str, detail: dict[str, Any], source: str = "application") -> None:
    db.add(AuditLog(organization_id=ctx["organization_id"], user_id=ctx["user"].id, action=action, detail=detail, source=source))
    db.execute(
        update(Organization)
        .where(Organization.id == ctx["organization_id"])
        .values(workspace_revision=Organization.workspace_revision + 1)
    )


def _workspace_revision(db: Session, organization_id: str) -> int:
    revision = db.scalar(select(Organization.workspace_revision).where(Organization.id == organization_id))
    return int(revision or 0)


def _record_out(record: DemoRecord) -> dict[str, Any]:
    return {"id": record.id, **record.payload, "is_demo": record.is_demo, "created_at": record.created_at.isoformat()}


def _workload_out(item: Workload) -> dict[str, Any]:
    return {
        "id": item.id, "project_id": item.project_id, "name": item.name, "task_type": item.task_type,
        "framework": item.framework, "status": item.status,
        **(item.requirements or {}), "requirements": item.requirements or {},
        "is_demo": item.is_demo, "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


def _scoped_workload(db: Session, workload_id: str, organization_id: str) -> Workload:
    item = db.scalar(select(Workload).where(Workload.id == workload_id, Workload.organization_id == organization_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Workload not found in this organization.")
    return item


def _demo_record(db: Session, organization_id: str, kind: str, record_id: str) -> DemoRecord:
    item = db.scalar(select(DemoRecord).where(DemoRecord.id == record_id, DemoRecord.organization_id == organization_id, DemoRecord.kind == kind))
    if item is None:
        raise HTTPException(status_code=404, detail="Record not found in this organization.")
    return item


def _validated_callback_origin(redirect_uri: str) -> tuple[str, str]:
    parsed = urlparse(redirect_uri)
    try:
        parsed.port
    except ValueError:
        raise HTTPException(status_code=400, detail="Use this app's /auth/callback URL for sign-in.")
    if parsed.scheme not in {"https", "http"} or not parsed.netloc or parsed.username or parsed.password or parsed.path != "/auth/callback" or parsed.query or parsed.fragment:
        raise HTTPException(status_code=400, detail="Use this app's /auth/callback URL for sign-in.")
    return parsed.scheme, parsed.netloc


def _owner_origin(redirect_uri: str, request: Request) -> str:
    scheme, netloc = _validated_callback_origin(redirect_uri)
    # Cloud Preview rebases Host to the internal listener. Validate against the browser origin
    # or same-origin Referer instead; never derive the public callback from request Host.
    candidates: list[tuple[str, str]] = []
    origin_header = request.headers.get("origin", "")
    if origin_header and origin_header.lower() != "null":
        origin = urlparse(origin_header)
        if origin.scheme in {"https", "http"} and origin.netloc and not origin.username and not origin.password and origin.path in {"", "/"} and not origin.query and not origin.fragment:
            candidates.append((origin.scheme, origin.netloc))
    referer = urlparse(request.headers.get("referer", ""))
    if referer.scheme in {"https", "http"} and referer.netloc and not referer.username and not referer.password:
        candidates.append((referer.scheme, referer.netloc))
    if not candidates:
        raise HTTPException(status_code=400, detail="The sign-in request must originate from this application.")
    if not any(candidate_scheme.lower() == scheme.lower() and candidate_netloc.lower() == netloc.lower() for candidate_scheme, candidate_netloc in candidates):
        raise HTTPException(status_code=400, detail="The sign-in callback origin must match the initiating application origin.")
    return f"{scheme}://{netloc}"


@router.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok", "service": "AstraDeploy API"}


def _build_oauth_start(request: Request, redirect_uri: str) -> tuple[str, str]:
    portal = os.getenv("MANUS_OAUTH_PORTAL_URL")
    app_id = os.getenv("MANUS_PROJECT_ID")
    if not portal or not app_id:
        raise HTTPException(status_code=503, detail="Manus OAuth is not configured in this runtime. Set up the project identity integration to sign in.")
    _owner_origin(redirect_uri, request)
    nonce = secrets.token_urlsafe(28)
    state = base64.urlsafe_b64encode(json.dumps({"redirectUri": redirect_uri, "nonce": nonce}).encode()).decode().rstrip("=")
    query = urlencode({"appId": app_id, "redirectUri": redirect_uri, "state": state, "responseType": "code"})
    return f"{portal.rstrip('/')}/app-auth?{query}", nonce


def _set_oauth_nonce(response: JSONResponse | RedirectResponse, request: Request, nonce: str) -> None:
    response.set_cookie("astra_oauth_nonce", nonce, httponly=True, secure=cookie_secure(request), samesite="lax", max_age=600, path="/")


@router.get("/auth/start")
def auth_start(request: Request, redirect_uri: str) -> RedirectResponse:
    authorization_url, nonce = _build_oauth_start(request, redirect_uri)
    response = RedirectResponse(authorization_url, status_code=302)
    _set_oauth_nonce(response, request, nonce)
    return response


@router.post("/auth/start")
def auth_start_post(request: Request, body: OAuthStartInput) -> JSONResponse:
    authorization_url, nonce = _build_oauth_start(request, body.redirect_uri)
    response = JSONResponse({"authorization_url": authorization_url})
    _set_oauth_nonce(response, request, nonce)
    return response


@router.post("/auth/complete")
async def auth_complete(request: Request, body: dict[str, str], db: Session = Depends(get_db)) -> JSONResponse:
    api_url = os.getenv("MANUS_OAUTH_API_URL")
    app_id = os.getenv("MANUS_PROJECT_ID")
    if not api_url or not app_id:
        raise HTTPException(status_code=503, detail="Manus OAuth is not configured in this runtime.")
    redirect_uri = body.get("redirect_uri", "")
    _validated_callback_origin(redirect_uri)
    raw_state = body.get("state", "")
    try:
        decoded = base64.urlsafe_b64decode(raw_state + "=" * (-len(raw_state) % 4))
        state = json.loads(decoded)
    except (ValueError, json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="The sign-in state is invalid. Restart sign-in.")
    if not isinstance(state, dict):
        raise HTTPException(status_code=400, detail="The sign-in state is invalid. Restart sign-in.")
    if state.get("redirectUri") != redirect_uri or not secrets.compare_digest(str(state.get("nonce", "")), request.cookies.get("astra_oauth_nonce", "")):
        raise HTTPException(status_code=400, detail="The sign-in state could not be verified. Restart sign-in.")
    code = body.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is missing.")
    oauth_stage = "authorization-code exchange"
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            exchange = await client.post(
                f"{api_url.rstrip('/')}/webdev.v1.WebDevAuthPublicService/ExchangeToken",
                json={"clientId": app_id, "grantType": "authorization_code", "code": code, "redirectUri": redirect_uri},
            )
            exchange.raise_for_status()
            exchanged = exchange.json()
            access_token = exchanged.get("accessToken")
            if not access_token:
                raise HTTPException(status_code=502, detail="Identity service did not return an access token.")
            oauth_stage = "identity profile lookup"
            identity_response = await client.post(
                f"{api_url.rstrip('/')}/webdev.v1.WebDevAuthPublicService/GetUserInfo",
                json={"accessToken": access_token},
            )
            identity_response.raise_for_status()
            identity = identity_response.json()
    except httpx.HTTPStatusError as exc:
        if oauth_stage == "authorization-code exchange" and exc.response.status_code == 401:
            detail = "Manus rejected the authorization code during token exchange (HTTP 401). Authorization codes are single-use and short-lived; restart sign-in. If a fresh code is also rejected, check the project's OAuth app registration."
        elif oauth_stage == "identity profile lookup" and exc.response.status_code == 401:
            detail = "Manus rejected the exchanged access token during profile lookup (HTTP 401). Restart sign-in; if this repeats, check the project's OAuth app registration."
        else:
            detail = f"Manus rejected the {oauth_stage} request (HTTP {exc.response.status_code})."
        raise HTTPException(status_code=502, detail=detail)
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Identity service is temporarily unavailable. Please retry sign-in.")
    open_id = identity.get("openId")
    if not open_id:
        raise HTTPException(status_code=502, detail="Identity service response did not include a user identifier.")
    user, membership = ensure_user_and_org(db, open_id=str(open_id), email=identity.get("email"), name=identity.get("name") or "AstraDeploy member")
    raw_session = create_session(db, user)
    _audit(db, {"organization_id": membership.organization_id, "user": user}, "auth.sign_in", {"identity_provider": "Manus OAuth"})
    db.commit()
    response = JSONResponse({"user": {"id": user.id, "name": user.name, "email": user.email, "role": membership.role}, "organization": {"id": membership.organization_id}})
    response.set_cookie(COOKIE_NAME, raw_session, httponly=True, secure=cookie_secure(request), samesite="none", max_age=14 * 24 * 3600, path="/")
    response.delete_cookie("astra_oauth_nonce", path="/")
    return response


@router.get("/auth/me")
def auth_me(ctx: dict[str, Any] = Depends(get_context)) -> dict[str, Any]:
    user, membership = ctx["user"], ctx["membership"]
    return {
        "user": {"id": user.id, "name": user.name, "email": user.email, "role": membership.role},
        "organization": {"id": membership.organization_id},
        "demo_mode": True,
        "identity_provider": "Manus OAuth",
    }


@router.post("/auth/logout")
def auth_logout(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        session = db.get(AppSession, _hash_token(token))
        if session:
            db.delete(session)
            db.commit()
    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE_NAME, path="/", secure=cookie_secure(request), httponly=True, samesite="none")
    return response


@router.get("/dashboard")
def dashboard(period: str = Query("7d", alias="range", pattern="^(24h|7d|30d)$"), ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> dict[str, Any]:
    org = ctx["organization_id"]
    workloads = list(db.scalars(select(Workload).where(Workload.organization_id == org).order_by(Workload.updated_at.desc())))
    deployments = list(db.scalars(select(Deployment).where(Deployment.organization_id == org)))
    pipelines = list(db.scalars(select(DemoRecord).where(DemoRecord.organization_id == org, DemoRecord.kind == "pipelines")))
    alerts = list(db.scalars(select(DemoRecord).where(DemoRecord.organization_id == org, DemoRecord.kind == "alerts")))
    charts = [
        {"day": "Mon", "cpu": 51, "memory": 58, "cost": 214}, {"day": "Tue", "cpu": 56, "memory": 62, "cost": 246},
        {"day": "Wed", "cpu": 49, "memory": 60, "cost": 238}, {"day": "Thu", "cpu": 64, "memory": 68, "cost": 279},
        {"day": "Fri", "cpu": 59, "memory": 65, "cost": 263}, {"day": "Sat", "cpu": 45, "memory": 51, "cost": 188},
        {"day": "Sun", "cpu": 63, "memory": 71, "cost": 292},
    ]
    if period == "24h":
        charts = [
            {"day": f"{hour:02d}:00", "cpu": 39 + (hour * 7 % 31), "memory": 48 + (hour * 5 % 29), "cost": 7 + (hour * 3 % 21)}
            for hour in range(0, 24, 2)
        ]
    elif period == "30d":
        charts = [
            {"day": f"{day:02d}", "cpu": 42 + (day * 11 % 30), "memory": 49 + (day * 7 % 31), "cost": 175 + (day * 29 % 130)}
            for day in range(1, 31)
        ]
    open_alerts = sum(1 for a in alerts if a.payload.get("status") == "Open")
    active_deployments = sum(1 for d in deployments if d.state == "Running") + sum(1 for d in db.scalars(select(DemoRecord).where(DemoRecord.organization_id == org, DemoRecord.kind == "deployments")) if d.payload.get("state") == "Running")
    active_pipelines = sum(1 for p in pipelines if p.payload.get("status") in {"Running", "Queued"})
    return {
        "source": "demo-seed-and-application-records",
        "is_demo": True,
        "summary": {"workloads": len(workloads), "deployments": active_deployments, "pipelines": active_pipelines, "cpu_percent": 63, "memory_percent": 71, "gpu_percent": 48, "estimated_monthly_spend_usd": 1840, "actual_spend_usd": None, "allocation_efficiency": 78, "optimization_opportunities": 3, "open_alerts": open_alerts},
        "resource_series": charts,
        "cost_series": charts,
        "workload_mix": [{"name": "Training", "value": 42}, {"name": "Inference", "value": 28}, {"name": "Batch", "value": 18}, {"name": "Other", "value": 12}],
        "provider_mix": [{"name": "AWS", "value": 46}, {"name": "Azure", "value": 30}, {"name": "GCP", "value": 24}],
        "recent_activity": [_record_out(r) for r in db.scalars(select(DemoRecord).where(DemoRecord.organization_id == org, DemoRecord.kind == "activity").order_by(DemoRecord.created_at.desc()).limit(5))],
    }


@router.get("/projects")
def list_projects(ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> dict[str, Any]:
    projects = db.scalars(select(Project).where(Project.organization_id == ctx["organization_id"]).order_by(Project.created_at))
    items = [{"id": p.id, "name": p.name, "description": p.description, "created_at": p.created_at.isoformat()} for p in projects]
    return {"items": items, "total": len(items)}


@router.post("/projects", status_code=201)
def create_project(body: ProjectInput, ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> dict[str, Any]:
    require_roles(ctx, EDITOR_ROLES)
    project = Project(organization_id=ctx["organization_id"], name=body.name.strip(), description=body.description.strip())
    db.add(project)
    db.flush()
    _audit(db, ctx, "project.created", {"project_id": project.id, "name": project.name})
    db.commit()
    db.refresh(project)
    return {"id": project.id, "name": project.name, "description": project.description, "created_at": project.created_at.isoformat()}


@router.get("/workloads")
def list_workloads(ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db), limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)) -> dict[str, Any]:
    org = ctx["organization_id"]
    total = db.scalar(select(func.count()).select_from(Workload).where(Workload.organization_id == org)) or 0
    items = db.scalars(select(Workload).where(Workload.organization_id == org).order_by(Workload.updated_at.desc()).offset(offset).limit(limit))
    return {"items": [_workload_out(i) for i in items], "total": total, "limit": limit, "offset": offset}


@router.post("/workloads", status_code=201)
def create_workload(body: WorkloadInput, ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> dict[str, Any]:
    require_roles(ctx, EDITOR_ROLES)
    if body.project_id:
        project = db.scalar(select(Project).where(Project.id == body.project_id, Project.organization_id == ctx["organization_id"]))
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found in this organization.")
    else:
        project = db.scalar(select(Project).where(Project.organization_id == ctx["organization_id"]).order_by(Project.created_at))
    item = Workload(organization_id=ctx["organization_id"], project_id=project.id if project else None, name=body.name, task_type=body.task_type, framework=body.framework, status="Ready", requirements=body.requirements(), is_demo=False)
    db.add(item)
    db.flush()
    _audit(db, ctx, "workload.created", {"workload_id": item.id, "name": item.name})
    db.commit()
    db.refresh(item)
    return _workload_out(item)


@router.post("/workloads/upload")
async def upload_workload(file: UploadFile = File(...), ctx: dict[str, Any] = Depends(get_context)) -> dict[str, Any]:
    require_roles(ctx, EDITOR_ROLES)
    filename = (file.filename or "").lower()
    allowed = (".yaml", ".yml", ".json", ".dockerfile", ".txt")
    if not filename.endswith(allowed) and not filename.endswith("dockerfile"):
        raise HTTPException(status_code=415, detail="Upload a .yaml, .yml, .json, Dockerfile or .txt configuration.")
    content = await file.read(1_000_001)
    if len(content) > 1_000_000:
        raise HTTPException(status_code=413, detail="Configuration file exceeds the 1 MB limit.")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Configuration must be UTF-8 text.")
    extracted: dict[str, Any] = {"name": (file.filename or "Imported workload").rsplit(".", 1)[0][:180], "task_type": "Imported configuration", "framework": "Detected from configuration", "dataset_gb": 48, "training_samples": 250000, "training_hours": 8, "cpu_cores": 4, "memory_gb": 16, "gpu_count": 0, "storage_gb": 100, "latency_ms": 250, "inference_rps": 0, "provider": "No preference", "budget_usd": 0, "availability": "Standard"}
    for key, target in (("cpu", "cpu_cores"), ("memory", "memory_gb"), ("nvidia.com/gpu", "gpu_count")):
        match = re.search(rf"(?:{re.escape(key)}|{re.escape(key.replace('.', r'\.'))})\s*[:=]\s*['\"]?(\d+)", text, re.IGNORECASE)
        if match:
            extracted[target] = int(match.group(1))
    return {"filename": file.filename, "bytes": len(content), "extracted": extracted, "analysis_note": "Best-effort text extraction only; review and confirm every imported requirement before saving."}


@router.post("/workloads/{workload_id}/analysis")
def run_analysis(workload_id: str, ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> dict[str, Any]:
    require_roles(ctx, EDITOR_ROLES)
    workload = _scoped_workload(db, workload_id, ctx["organization_id"])
    result = analyze_workload({**workload.requirements, "task_type": workload.task_type})
    result["limitations"] = ["No connected historical metrics or live price catalog; estimates use documented rules and illustrative demo rates."]
    record = WorkloadAnalysis(organization_id=ctx["organization_id"], workload_id=workload.id, result=result)
    db.add(record)
    workload.status = "Analyzed"
    _audit(db, ctx, "workload.analyzed", {"workload_id": workload.id, "analysis_id": record.id})
    db.commit()
    return {"id": record.id, "workload_id": workload.id, **result, "source": "rule-based", "is_demo": workload.is_demo}


@router.post("/workloads/{workload_id}/recommendations")
def recommend(workload_id: str, ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> dict[str, Any]:
    require_roles(ctx, EDITOR_ROLES)
    workload = _scoped_workload(db, workload_id, ctx["organization_id"])
    choices = build_recommendations({**workload.requirements, "task_type": workload.task_type})
    saved = []
    for item in choices:
        row = Recommendation(organization_id=ctx["organization_id"], workload_id=workload.id, tier=item["tier"], configuration=item, monthly_estimate_usd=item["estimated_cost_usd"], rationale=item["rationale"], evidence=item["confidence"], is_demo=True)
        db.add(row)
        db.flush()
        saved.append({"id": row.id, **item, "is_demo": True})
    _audit(db, ctx, "recommendations.generated", {"workload_id": workload.id, "tiers": [x["tier"] for x in choices]})
    db.commit()
    return {"workload_id": workload.id, "recommendations": saved, "source": "deterministic-rules", "is_demo": True}


@router.get("/recommendations")
def list_recommendations(ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> dict[str, Any]:
    rows = db.scalars(select(Recommendation).where(Recommendation.organization_id == ctx["organization_id"]).order_by(Recommendation.created_at.desc()).limit(60))
    return {"items": [{"id": x.id, "workload_id": x.workload_id, "tier": x.tier, **x.configuration, "selected": x.selected, "is_demo": x.is_demo, "created_at": x.created_at.isoformat()} for x in rows]}


@router.post("/recommendations/{recommendation_id}/select")
def select_recommendation(recommendation_id: str, ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> dict[str, Any]:
    require_roles(ctx, EDITOR_ROLES)
    item = db.scalar(select(Recommendation).where(Recommendation.id == recommendation_id, Recommendation.organization_id == ctx["organization_id"]))
    if item is None:
        raise HTTPException(status_code=404, detail="Recommendation not found in this organization.")
    for other in db.scalars(select(Recommendation).where(Recommendation.workload_id == item.workload_id)):
        other.selected = other.id == item.id
    _audit(db, ctx, "recommendation.selected", {"recommendation_id": item.id, "tier": item.tier})
    db.commit()
    return {"ok": True, "selected_id": item.id, "tier": item.tier}


@router.post("/recommendations/{recommendation_id}/plan")
def preview_plan(recommendation_id: str, ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> dict[str, Any]:
    require_roles(ctx, OPERATOR_ROLES)
    item = db.scalar(select(Recommendation).where(Recommendation.id == recommendation_id, Recommendation.organization_id == ctx["organization_id"]))
    if item is None:
        raise HTTPException(status_code=404, detail="Recommendation not found in this organization.")
    if not item.selected:
        raise HTTPException(status_code=409, detail="Select this recommendation before reviewing a provisioning plan.")
    if not item.configuration.get("fits_budget", False):
        raise HTTPException(status_code=409, detail="This recommendation exceeds the submitted budget. Adjust the budget or select a plan that fits before reviewing a plan preview.")
    job = DemoRecord(organization_id=ctx["organization_id"], kind="provisioning", payload={"name": item.tier + " resource plan", "recommendation_id": item.id, "state": "Plan preview ready", "mode": "demo-simulation", "real_resources_created": False, "estimated_cost_usd": item.monthly_estimate_usd, "created_at": datetime.now(timezone.utc).isoformat(), "steps": ["Validate workload constraints", "Check illustrative budget policy", "Render Terraform/Kubernetes preview", "Await configured integration and separate authorization"]})
    db.add(job)
    _audit(db, ctx, "provisioning.preview_created", {"recommendation_id": item.id, "simulation": True})
    db.commit()
    return _record_out(job)


@router.get("/records/{kind}")
def list_records(kind: str, ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db), limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)) -> dict[str, Any]:
    if kind not in RECORD_KINDS:
        raise HTTPException(status_code=404, detail="Unknown record collection.")
    rows = db.scalars(select(DemoRecord).where(DemoRecord.organization_id == ctx["organization_id"], DemoRecord.kind == kind).order_by(DemoRecord.updated_at.desc()).offset(offset).limit(limit))
    return {"items": [_record_out(x) for x in rows], "total": len(list(db.scalars(select(DemoRecord).where(DemoRecord.organization_id == ctx["organization_id"], DemoRecord.kind == kind)))), "source": "demo records"}


@router.post("/records", status_code=201)
def create_record(body: RecordCreate, ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> dict[str, Any]:
    require_roles(ctx, EDITOR_ROLES)
    item = DemoRecord(organization_id=ctx["organization_id"], kind=body.kind, payload={**body.payload, "mode": "demo"}, is_demo=True)
    db.add(item)
    _audit(db, ctx, f"{body.kind}.created", {"record_id": item.id, "demo": True})
    db.commit()
    db.refresh(item)
    return _record_out(item)


@router.post("/actions")
def action(body: ActionInput, ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> dict[str, Any]:
    action_name = body.action
    if action_name in {"run_pipeline", "apply_optimization", "dismiss_optimization", "acknowledge_alert", "resolve_alert"}:
        require_roles(ctx, OPERATOR_ROLES)
    else:
        require_roles(ctx, EDITOR_ROLES)
    item: DemoRecord | None = None
    if action_name == "create_budget":
        name = str(body.payload.get("name", "Project budget"))[:180]
        limit = float(body.payload.get("limit_usd", 0))
        if limit <= 0:
            raise HTTPException(status_code=422, detail="Budget limit must be greater than zero.")
        item = DemoRecord(organization_id=ctx["organization_id"], kind="budgets", payload={"name": name, "scope": body.payload.get("scope", "Project"), "limit_usd": limit, "spent_usd": 0, "thresholds": [50, 75, 90, 100], "mode": "demo-policy"}, is_demo=True)
        db.add(item)
    elif action_name == "create_deployment":
        item = DemoRecord(organization_id=ctx["organization_id"], kind="deployments", payload={"name": str(body.payload.get("name", "Model deployment"))[:180], "model": body.payload.get("model", "Unassigned"), "environment": body.payload.get("environment", "Development"), "state": "Draft", "provider": "Not connected", "endpoint": None, "mode": "demo"}, is_demo=True)
        db.add(item)
    elif action_name == "run_pipeline":
        item = _demo_record(db, ctx["organization_id"], "pipelines", body.record_id or "")
        item.payload = {**item.payload, "status": "Running (simulated)", "progress": min(95, int(item.payload.get("progress", 0)) + 25), "updated": "Just now", "mode": "demo-simulation"}
    elif action_name in {"acknowledge_alert", "resolve_alert"}:
        item = _demo_record(db, ctx["organization_id"], "alerts", body.record_id or "")
        item.payload = {**item.payload, "status": "Acknowledged" if action_name == "acknowledge_alert" else "Resolved", "mode": "demo"}
    elif action_name in {"apply_optimization", "dismiss_optimization"}:
        item = _demo_record(db, ctx["organization_id"], "optimizations", body.record_id or "")
        next_state = "Applied (simulated)" if action_name == "apply_optimization" else "Dismissed"
        item.payload = {**item.payload, "status": next_state, "mode": "demo-simulation" if action_name == "apply_optimization" else "demo"}
    else:
        raise HTTPException(status_code=422, detail="Unsupported action.")
    _audit(db, ctx, action_name, {"record_id": item.id if item else None, "simulation": action_name in {"run_pipeline", "apply_optimization"}})
    db.commit()
    if item:
        db.refresh(item)
        return _record_out(item)
    return {"ok": True}


@router.get("/team")
def team(ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> dict[str, Any]:
    members = db.scalars(select(Membership).where(Membership.organization_id == ctx["organization_id"]))
    rows = []
    for m in members:
        user = db.get(User, m.user_id)
        if user:
            rows.append({"id": user.id, "name": user.name, "email": user.email, "role": m.role, "joined_at": m.created_at.isoformat()})
    return {"items": rows, "total": len(rows), "note": "Organization membership is enforced by backend authorization."}


@router.patch("/team/{user_id}/role")
def update_team_role(user_id: str, body: RoleUpdate, ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> dict[str, Any]:
    require_roles(ctx, {"Admin"})
    membership = db.scalar(select(Membership).where(Membership.user_id == user_id, Membership.organization_id == ctx["organization_id"]))
    if membership is None:
        raise HTTPException(status_code=404, detail="Member not found in this organization.")
    if user_id == ctx["user"].id and body.role != membership.role:
        raise HTTPException(status_code=409, detail="Sign out and use a second organization administrator to change your own role.")
    if membership.role == "Admin" and body.role != "Admin":
        admin_count = db.scalar(select(func.count()).select_from(Membership).where(Membership.organization_id == ctx["organization_id"], Membership.role == "Admin")) or 0
        if admin_count <= 1:
            raise HTTPException(status_code=409, detail="An organization must retain at least one administrator.")
    membership.role = body.role
    _audit(db, ctx, "member.role_updated", {"user_id": user_id, "role": body.role})
    db.commit()
    return {"user_id": user_id, "role": membership.role, "organization_id": membership.organization_id}


@router.get("/settings")
def settings(ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> dict[str, Any]:
    org = db.get(Organization, ctx["organization_id"])
    return {"organization": {"id": org.id, "name": org.name} if org else None, "role": ctx["role"], "integrations": SAMPLE_RECORDS["integrations"], "mode": "demo", "database": "managed MySQL-compatible database or configured DATABASE_URL", "live_cloud_actions_enabled": False}


@router.get("/audit")
def audit_logs(ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db), limit: int = Query(100, ge=1, le=500)) -> dict[str, Any]:
    rows = db.scalars(select(AuditLog).where(AuditLog.organization_id == ctx["organization_id"]).order_by(AuditLog.created_at.desc()).limit(limit))
    return {"items": [{"id": x.id, "action": x.action, "detail": x.detail, "source": x.source, "created_at": x.created_at.isoformat()} for x in rows]}


@router.get("/workspace")
def workspace_snapshot(period: str = Query("7d", alias="range", pattern="^(24h|7d|30d)$"), ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return the authenticated tenant's app data in one consistent API response."""
    return {
        "revision": _workspace_revision(db, ctx["organization_id"]),
        "dashboard": dashboard(period, ctx, db),
        "workloads": list_workloads(ctx, db, limit=100, offset=0),
        "records": {kind: list_records(kind, ctx, db, limit=100, offset=0)["items"] for kind in sorted(RECORD_KINDS)},
        "team": team(ctx, db),
        "settings": settings(ctx, db),
        "audit": audit_logs(ctx, db, limit=100),
    }


@router.get("/workspace/events")
async def workspace_events(request: Request, ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> StreamingResponse:
    """Stream tenant workspace change notices; clients fetch the snapshot after each notice."""
    organization_id = ctx["organization_id"]

    async def event_stream():
        last_revision = _workspace_revision(db, organization_id)
        db.commit()
        # Emit a sync notice on connect/reconnect to close the snapshot-to-stream race.
        yield "data: " + json.dumps({"type": "workspace.updated", "revision": last_revision, "reason": "connected"}, separators=(",", ":")) + "\n\n"
        last_heartbeat = time.monotonic()
        while not await request.is_disconnected():
            await asyncio.sleep(2)
            if await request.is_disconnected():
                break
            current_revision = _workspace_revision(db, organization_id)
            db.commit()
            if current_revision != last_revision:
                last_revision = current_revision
                yield "data: " + json.dumps({"type": "workspace.updated", "revision": last_revision}, separators=(",", ":")) + "\n\n"
                last_heartbeat = time.monotonic()
            elif time.monotonic() - last_heartbeat >= 15:
                yield ": keep-alive\n\n"
                last_heartbeat = time.monotonic()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.post("/reports/generate", status_code=201)
def generate_report(body: ReportInput, ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> dict[str, Any]:
    require_roles(ctx, EDITOR_ROLES)
    workload_count = db.scalar(select(func.count()).select_from(Workload).where(Workload.organization_id == ctx["organization_id"])) or 0
    organization_id = ctx["organization_id"]
    counts = {
        "recommendations": db.scalar(select(func.count()).select_from(Recommendation).where(Recommendation.organization_id == organization_id)) or 0,
        "optimizations": db.scalar(select(func.count()).select_from(DemoRecord).where(DemoRecord.organization_id == organization_id, DemoRecord.kind == "optimizations")) or 0,
        "deployments": db.scalar(select(func.count()).select_from(Deployment).where(Deployment.organization_id == organization_id)) or 0,
        "pipelines": db.scalar(select(func.count()).select_from(DemoRecord).where(DemoRecord.organization_id == organization_id, DemoRecord.kind == "pipelines")) or 0,
        "audit": db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.organization_id == organization_id)) or 0,
    }
    findings_by_type = {
        "Workload analysis": [f"{workload_count} registered workload requirements are in this organization.", "Historical live utilization is not connected; no measured training profile is claimed."],
        "Resource recommendations": [f"{counts['recommendations']} persisted recommendations are in this organization.", "Recommendations are deterministic rule-based plans, not validated cloud availability or live pricing."],
        "Cost optimization": [f"{counts['optimizations']} optimization records are in this organization.", "Savings and cost deltas are illustrative estimates; no provider billing was queried."],
        "Deployment summary": [f"{counts['deployments']} deployment records are in this organization.", "Demo deployments are not live endpoints; no cloud deployment or resource changes occurred."],
        "Pipeline execution": [f"{counts['pipelines']} pipeline records are in this organization.", "Pipeline progress is simulated; user code is not executed."],
        "Audit activity": [f"{counts['audit']} audit events are recorded in this organization.", "This snapshot is organization-scoped and includes no provider secrets."],
    }
    report = DemoRecord(organization_id=organization_id, kind="reports", payload={"name": f"{body.report_type} report", "type": body.report_type, "generated_at": datetime.now(timezone.utc).isoformat(), "findings": [*findings_by_type[body.report_type], "Provider billing and telemetry are not connected; figures are labeled estimates or demo records."], "format": "JSON / CSV", "mode": "demo"}, is_demo=True)
    db.add(report)
    _audit(db, ctx, "report.generated", {"report_id": report.id, "type": report.payload["type"]})
    db.commit()
    db.refresh(report)
    return _record_out(report)


@router.get("/reports/export")
def export_report(fmt: str = Query("json", pattern="^(json|csv)$"), ctx: dict[str, Any] = Depends(get_context), db: Session = Depends(get_db)) -> StreamingResponse:
    workloads = [_workload_out(x) for x in db.scalars(select(Workload).where(Workload.organization_id == ctx["organization_id"]))]
    if fmt == "csv":
        buffer = io.StringIO()
        fields = ["id", "name", "task_type", "framework", "status", "is_demo", "created_at"]
        writer = csv.DictWriter(buffer, fieldnames=fields)
        writer.writeheader()
        for item in workloads:
            writer.writerow({key: item.get(key, "") for key in fields})
        return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=astradeploy-workloads.csv"})
    return StreamingResponse(iter([json.dumps({"report": "AstraDeploy workload export", "generated_at": datetime.now(timezone.utc).isoformat(), "data_kind": "demo or user-provided requirements; no connected billing data", "workloads": workloads}, indent=2)]), media_type="application/json", headers={"Content-Disposition": "attachment; filename=astradeploy-workloads.json"})
