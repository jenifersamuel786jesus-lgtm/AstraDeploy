from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from typing import cast

import pytest
import httpx
import jwt
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from backend.app.api.routes import RECORD_KINDS, _workspace_revision, get_context, router, workspace_events
from backend.app.core.database import Base, get_db
from backend.app.core.security import COOKIE_NAME, _hash_token, create_session, resolve_user
from backend.app.models.entities import AppSession, DemoRecord, Membership, Organization, Project, User, Workload


TEST_ENGINE = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TEST_SESSIONS = sessionmaker(bind=TEST_ENGINE, autoflush=False, expire_on_commit=False)
CURRENT_ROLE = "Admin"
CURRENT_ORG = "org-a"
TEST_APP = FastAPI()
TEST_APP.include_router(router)


def override_db() -> Generator[Session, None, None]:
    with TEST_SESSIONS() as db:
        yield db


def override_context() -> dict[str, object]:
    return {
        "user": SimpleNamespace(id="user-a", name="Admin Tester", email="admin@example.test"),
        "membership": SimpleNamespace(user_id="user-a", organization_id=CURRENT_ORG, role=CURRENT_ROLE),
        "organization_id": CURRENT_ORG,
        "role": CURRENT_ROLE,
    }


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    global CURRENT_ROLE, CURRENT_ORG
    CURRENT_ROLE, CURRENT_ORG = "Admin", "org-a"
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)
    with TEST_SESSIONS() as db:
        db.add_all([
            Organization(id="org-a", name="Alpha Org"), Organization(id="org-b", name="Beta Org"),
            User(id="user-a", open_id="test-open-id", email="admin@example.test", name="Admin Tester"),
            Project(id="project-a", organization_id="org-a", name="ML Platform", description="Default project"),
            Project(id="project-b", organization_id="org-b", name="Beta Project", description="Other tenant"),
        ])
        db.add(Membership(id="member-a", user_id="user-a", organization_id="org-a", role="Admin"))
        db.commit()
    TEST_APP.dependency_overrides[get_db] = override_db
    TEST_APP.dependency_overrides[get_context] = override_context
    with TestClient(TEST_APP) as test_client:
        yield test_client
    TEST_APP.dependency_overrides.clear()


def workload_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Demand forecaster", "project_id": "project-a", "task_type": "Traditional ML training",
        "framework": "XGBoost", "dataset_gb": 10, "training_samples": 100000,
        "training_hours": 2, "cpu_cores": 4, "memory_gb": 16, "gpu_count": 0,
        "storage_gb": 30, "latency_ms": 250, "inference_rps": 0, "provider": "No preference",
        "budget_usd": 100, "availability": "Standard",
    }
    payload.update(overrides)
    return payload


def test_projects_are_tenant_scoped_and_creatable(client: TestClient) -> None:
    listed = client.get("/api/v1/projects")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == ["project-a"]
    created = client.post("/api/v1/projects", json={"name": "Vision Models", "description": "Model delivery"})
    assert created.status_code == 201
    assert created.json()["name"] == "Vision Models"
    assert client.get("/api/v1/projects").json()["total"] == 2


def test_workload_registration_and_validation(client: TestClient) -> None:
    response = client.post("/api/v1/workloads", json=workload_payload())
    assert response.status_code == 201
    assert response.json()["project_id"] == "project-a"
    assert response.json()["is_demo"] is False
    invalid = client.post("/api/v1/workloads", json=workload_payload(dataset_gb=0))
    assert invalid.status_code == 422
    wrong_project = client.post("/api/v1/workloads", json=workload_payload(project_id="project-b"))
    assert wrong_project.status_code == 404


def test_viewer_is_read_only_for_project_and_workload_writes(client: TestClient) -> None:
    global CURRENT_ROLE
    CURRENT_ROLE = "Viewer"
    assert client.post("/api/v1/projects", json={"name": "Blocked project"}).status_code == 403
    assert client.post("/api/v1/workloads", json=workload_payload()).status_code == 403
    assert client.patch("/api/v1/team/user-a/role", json={"role": "Viewer"}).status_code == 403


def test_admin_role_changes_are_tenant_scoped_and_preserve_admin_access(client: TestClient) -> None:
    with TEST_SESSIONS() as db:
        db.add(User(id="user-b", open_id="second-open-id", email="member@example.test", name="Team Member"))
        db.add(Membership(id="member-b", user_id="user-b", organization_id="org-a", role="ML/DevOps Engineer"))
        db.commit()
    updated = client.patch("/api/v1/team/user-b/role", json={"role": "Viewer"})
    assert updated.status_code == 200
    assert updated.json()["role"] == "Viewer"
    assert client.patch("/api/v1/team/user-b/role", json={"role": "Unsupported"}).status_code == 422
    self_change = client.patch("/api/v1/team/user-a/role", json={"role": "Viewer"})
    assert self_change.status_code == 409
    assert client.patch("/api/v1/team/not-in-org/role", json={"role": "Viewer"}).status_code == 404


def test_other_organization_workloads_are_not_disclosed(client: TestClient) -> None:
    with TEST_SESSIONS() as db:
        other = Workload(id="workload-b", organization_id="org-b", project_id="project-b", name="Private workload", task_type="Training", framework="PyTorch", requirements={"cpu_cores": 4}, is_demo=False)
        db.add(other)
        db.commit()
    response = client.post("/api/v1/workloads/workload-b/analysis")
    assert response.status_code == 404
    assert client.get("/api/v1/workloads").json()["total"] == 0


def test_rule_based_recommendations_enforce_budget_before_plan_preview(client: TestClient) -> None:
    workload = client.post("/api/v1/workloads", json=workload_payload(budget_usd=1)).json()
    generated = client.post(f"/api/v1/workloads/{workload['id']}/recommendations")
    assert generated.status_code == 200
    options = generated.json()["recommendations"]
    assert len(options) == 3
    assert {item["tier"] for item in options} == {"Cost-optimized", "Balanced", "Performance-optimized"}
    assert all(item["confidence"].startswith("Rule-based") for item in options)
    chosen = options[1]
    assert chosen["fits_budget"] is False
    assert client.post(f"/api/v1/recommendations/{chosen['id']}/select").status_code == 200
    rejected = client.post(f"/api/v1/recommendations/{chosen['id']}/plan")
    assert rejected.status_code == 409
    assert "exceeds" in rejected.json()["detail"]


def test_approved_budget_fit_creates_only_a_plan_preview(client: TestClient) -> None:
    workload = client.post("/api/v1/workloads", json=workload_payload(budget_usd=500)).json()
    options = client.post(f"/api/v1/workloads/{workload['id']}/recommendations").json()["recommendations"]
    chosen = options[1]
    assert chosen["fits_budget"] is True
    client.post(f"/api/v1/recommendations/{chosen['id']}/select")
    plan = client.post(f"/api/v1/recommendations/{chosen['id']}/plan")
    assert plan.status_code == 200
    assert plan.json()["real_resources_created"] is False
    assert plan.json()["mode"] == "demo-simulation"


def test_dashboard_time_windows_and_budget_policy(client: TestClient) -> None:
    assert len(client.get("/api/v1/dashboard?range=24h").json()["resource_series"]) == 12
    assert len(client.get("/api/v1/dashboard?range=7d").json()["resource_series"]) == 7
    assert len(client.get("/api/v1/dashboard?range=30d").json()["resource_series"]) == 30
    assert client.get("/api/v1/dashboard?range=all").status_code == 422
    action = client.post("/api/v1/actions", json={"action": "create_budget", "payload": {"name": "Inference", "limit_usd": 1500, "scope": "Project"}})
    assert action.status_code == 200
    assert action.json()["limit_usd"] == 1500
    bad = client.post("/api/v1/actions", json={"action": "create_budget", "payload": {"limit_usd": 0}})
    assert bad.status_code == 422


def test_report_export_is_explicitly_labeled_json_or_csv(client: TestClient) -> None:
    client.post("/api/v1/workloads", json=workload_payload())
    csv_response = client.get("/api/v1/reports/export?fmt=csv")
    json_response = client.get("/api/v1/reports/export?fmt=json")
    assert csv_response.status_code == json_response.status_code == 200
    assert "is_demo" in csv_response.text
    assert "demo or user-provided requirements" in json_response.text
    assert client.get("/api/v1/reports/export?fmt=xml").status_code == 422


def test_persisted_session_expiry_is_timezone_safe_and_expired_session_can_logout(client: TestClient) -> None:
    with TEST_SESSIONS() as db:
        user = db.get(User, "user-a")
        assert user is not None
        token = create_session(db, user)
        request = Request({"type": "http", "headers": [(b"cookie", f"{COOKIE_NAME}={token}".encode())]})
        resolved, _ = resolve_user(request, db)
        assert resolved.id == "user-a"
        persisted = db.get(AppSession, _hash_token(token))
        assert persisted is not None
        persisted.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
        with pytest.raises(HTTPException) as expired:
            resolve_user(request, db)
        assert expired.value.status_code == 401
    client.cookies.set(COOKIE_NAME, token)
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    with TEST_SESSIONS() as db:
        assert db.get(AppSession, _hash_token(token)) is None


def test_data_scientist_cannot_run_operator_actions(client: TestClient) -> None:
    global CURRENT_ROLE
    CURRENT_ROLE = "Data Scientist/Developer"
    pipeline = client.post("/api/v1/records", json={"kind": "pipelines", "payload": {"name": "Demo pipeline", "status": "Queued"}})
    assert pipeline.status_code == 201
    run = client.post("/api/v1/actions", json={"action": "run_pipeline", "record_id": pipeline.json()["id"]})
    assert run.status_code == 403
    with TEST_SESSIONS() as db:
        db.add(DemoRecord(id="optimization-a", organization_id="org-a", kind="optimizations", payload={"name": "Right-size", "status": "Open"}, is_demo=True))
        db.commit()
    assert client.post("/api/v1/actions", json={"action": "apply_optimization", "record_id": "optimization-a"}).status_code == 403


def test_report_type_card_is_preserved_in_saved_report(client: TestClient) -> None:
    response = client.post("/api/v1/reports/generate", json={"report_type": "Cost optimization"})
    assert response.status_code == 201
    assert response.json()["name"] == "Cost optimization report"
    assert response.json()["type"] == "Cost optimization"
    assert "no provider billing was queried" in " ".join(response.json()["findings"])
    assert client.post("/api/v1/reports/generate", json={"report_type": "PDF report"}).status_code == 422


def test_audited_mutation_advances_only_its_organization_revision(client: TestClient) -> None:
    with TEST_SESSIONS() as db:
        starting_revision = _workspace_revision(db, "org-a")
        other_revision = _workspace_revision(db, "org-b")
    created = client.post("/api/v1/projects", json={"name": "Realtime revision", "description": "SSE test"})
    assert created.status_code == 201
    with TEST_SESSIONS() as db:
        assert _workspace_revision(db, "org-a") == starting_revision + 1
        assert _workspace_revision(db, "org-b") == other_revision


def test_workspace_event_stream_emits_a_sync_notice(client: TestClient) -> None:
    async def read_events() -> tuple[dict[str, str], str, str]:
        with TEST_SESSIONS() as db:
            class ConnectedRequest(Request):
                async def is_disconnected(self) -> bool:
                    return False

            request = ConnectedRequest({"type": "http", "method": "GET", "headers": []})
            response = await workspace_events(request, override_context(), db)
            stream = cast(AsyncGenerator[str, None], response.body_iterator)
            connected_event = await anext(stream)
            created = await asyncio.to_thread(
                client.post,
                "/api/v1/projects",
                json={"name": "SSE event delivery", "description": "Real-time stream test"},
            )
            assert created.status_code == 201
            update_event = await anext(stream)
            await stream.aclose()
            return dict(response.headers), str(connected_event), str(update_event)

    headers, connected_event, update_event = asyncio.run(read_events())
    assert headers["content-type"].startswith("text/event-stream")
    assert headers["cache-control"] == "no-cache, no-transform"
    assert '"type":"workspace.updated"' in connected_event
    assert '"reason":"connected"' in connected_event
    assert '"revision":1' in update_event


def test_workspace_event_route_requires_authentication() -> None:
    auth_app = FastAPI()
    auth_app.include_router(router)
    auth_app.dependency_overrides[get_db] = override_db
    with TestClient(auth_app) as anonymous:
        response = anonymous.get("/api/v1/workspace/events")
    assert response.status_code == 401


def test_preview_identity_first_login_loads_every_workspace_api(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "test-only-preview-jwt-secret"
    app_id = "astradeploy-preview-test"
    monkeypatch.setenv("MANUS_JWT_SECRET", secret)
    monkeypatch.setenv("MANUS_PROJECT_ID", app_id)
    signed_preview_token = jwt.encode(
        {"appId": app_id, "openId": "preview-workspace-api-test", "exp": datetime.now(timezone.utc) + timedelta(minutes=2)},
        secret,
        algorithm="HS256",
    )
    auth_app = FastAPI()
    auth_app.include_router(router)
    auth_app.dependency_overrides[get_db] = override_db
    with TestClient(auth_app) as authenticated:
        authenticated.cookies.set(COOKIE_NAME, signed_preview_token)
        identity = authenticated.get("/api/v1/auth/me")
        assert identity.status_code == 200, identity.text
        assert identity.json()["user"]["role"] == "Admin"
        snapshot = authenticated.get("/api/v1/workspace?range=7d")
        assert snapshot.status_code == 200, snapshot.text
        payload = snapshot.json()
        assert isinstance(payload["revision"], int)
        assert payload["dashboard"]["is_demo"] is True
        assert payload["workloads"]["total"] == 4
        assert set(payload["records"]) == set(RECORD_KINDS)
        assert payload["settings"]["organization"]["id"]
        assert payload["settings"]["role"] == "Admin"
        assert payload["team"]["total"] == 1
        endpoints = ["/api/v1/dashboard", "/api/v1/projects", "/api/v1/workloads", "/api/v1/recommendations", "/api/v1/team", "/api/v1/settings", "/api/v1/audit", "/api/v1/reports/export"]
        endpoints.extend(f"/api/v1/records/{kind}" for kind in RECORD_KINDS)
        for path in endpoints:
            response = authenticated.get(path)
            assert response.status_code == 200, f"{path}: {response.status_code} {response.text}"


def test_oauth_callback_origin_is_bound_to_initiating_app(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MANUS_OAUTH_PORTAL_URL", "https://identity.example.test")
    monkeypatch.setenv("MANUS_PROJECT_ID", "astradeploy-test-app")
    callback = "https://preview.example.test/auth/callback"
    rejected = client.get(
        "/api/v1/auth/start",
        params={"redirect_uri": callback.replace("preview.example.test", "attacker.example.test")},
        headers={"referer": "https://preview.example.test/"},
        follow_redirects=False,
    )
    assert rejected.status_code == 400
    unbound = client.get("/api/v1/auth/start", params={"redirect_uri": callback}, follow_redirects=False)
    assert unbound.status_code == 400
    accepted = client.get(
        "/api/v1/auth/start",
        params={"redirect_uri": callback},
        headers={"referer": "https://preview.example.test/workloads"},
        follow_redirects=False,
    )
    assert accepted.status_code == 302
    assert accepted.headers["location"].startswith("https://identity.example.test/app-auth?")
    assert "redirectUri=https%3A%2F%2Fpreview.example.test%2Fauth%2Fcallback" in accepted.headers["location"]


def test_oauth_start_post_uses_browser_origin_behind_preview_proxy(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MANUS_OAUTH_PORTAL_URL", "https://identity.example.test")
    monkeypatch.setenv("MANUS_PROJECT_ID", "astradeploy-test-app")
    callback = "https://preview.example.test/auth/callback"
    accepted = client.post(
        "/api/v1/auth/start",
        json={"redirect_uri": callback},
        headers={"origin": "https://preview.example.test", "referer": "https://preview.example.test/"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["authorization_url"].startswith("https://identity.example.test/app-auth?")
    assert "redirectUri=https%3A%2F%2Fpreview.example.test%2Fauth%2Fcallback" in accepted.json()["authorization_url"]
    assert accepted.cookies.get("astra_oauth_nonce")
    proxy_rewritten_origin = client.post(
        "/api/v1/auth/start",
        json={"redirect_uri": callback},
        headers={"origin": "https://dashboard.example.test", "referer": "https://preview.example.test/workloads"},
    )
    assert proxy_rewritten_origin.status_code == 200
    rejected = client.post(
        "/api/v1/auth/start",
        json={"redirect_uri": callback},
        headers={"origin": "https://attacker.example.test"},
    )
    assert rejected.status_code == 400


def test_oauth_completion_uses_validated_state_and_nonce_when_proxy_rewrites_origin(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MANUS_OAUTH_PORTAL_URL", "https://identity.example.test")
    monkeypatch.setenv("MANUS_OAUTH_API_URL", "https://identity.example.test")
    monkeypatch.setenv("MANUS_PROJECT_ID", "astradeploy-test-app")
    callback = "https://preview.example.test/auth/callback"
    start = client.get(
        "/api/v1/auth/start",
        params={"redirect_uri": callback},
        headers={"referer": "https://preview.example.test/"},
        follow_redirects=False,
    )
    assert start.status_code == 302
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    nonce = start.cookies.get("astra_oauth_nonce")
    assert nonce

    class FakeOAuthResponse:
        def __init__(self, payload: dict[str, str]) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return self.payload

    async def fake_post(_self: object, url: str, *, json: dict[str, str]) -> FakeOAuthResponse:
        if url.endswith("/ExchangeToken"):
            assert json["redirectUri"] == callback
            return FakeOAuthResponse({"accessToken": "test-access-token"})
        if url.endswith("/GetUserInfo"):
            return FakeOAuthResponse({"openId": "oauth-user-123", "name": "OAuth Tester", "email": "oauth@example.test"})
        raise AssertionError("Unexpected OAuth service endpoint")

    monkeypatch.setattr("backend.app.api.routes.httpx.AsyncClient.post", fake_post)
    completed = client.post(
        "/api/v1/auth/complete",
        json={"code": "test-code", "state": state, "redirect_uri": callback},
        headers={"origin": "https://dashboard.example.test", "cookie": f"astra_oauth_nonce={nonce}"},
    )
    assert completed.status_code == 200
    assert completed.json()["user"]["name"] == "OAuth Tester"

    retry_start = client.get(
        "/api/v1/auth/start",
        params={"redirect_uri": callback},
        headers={"referer": "https://preview.example.test/"},
        follow_redirects=False,
    )
    retry_state = parse_qs(urlsplit(retry_start.headers["location"]).query)["state"][0]
    retry_nonce = retry_start.cookies.get("astra_oauth_nonce")
    assert retry_nonce

    async def reject_exchange(_self: object, url: str, *, json: dict[str, str]) -> httpx.Response:
        request = httpx.Request("POST", url)
        return httpx.Response(401, request=request, json={"error": "invalid_grant"})

    monkeypatch.setattr("backend.app.api.routes.httpx.AsyncClient.post", reject_exchange)
    rejected = client.post(
        "/api/v1/auth/complete",
        json={"code": "expired-code", "state": retry_state, "redirect_uri": callback},
        headers={"origin": "https://dashboard.example.test", "cookie": f"astra_oauth_nonce={retry_nonce}"},
    )
    assert rejected.status_code == 502
    assert "authorization code during token exchange" in rejected.json()["detail"]
    assert "single-use" in rejected.json()["detail"]
