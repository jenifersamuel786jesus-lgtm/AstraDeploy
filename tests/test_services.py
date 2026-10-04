from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from backend.app.adapters.cloud import AWSAdapter, ProviderNotConfigured
from backend.app.core.database import database_engine_parts
from backend.app.core.security import _preview_identity
from backend.app.services.recommendation import analyze_workload, build_recommendations


def base_requirements(**overrides: object) -> dict[str, object]:
    requirements: dict[str, object] = {
        "task_type": "Traditional ML training", "framework": "XGBoost", "training_samples": 100000,
        "dataset_gb": 16, "training_hours": 2, "cpu_cores": 4, "memory_gb": 8,
        "gpu_count": 0, "storage_gb": 32, "provider": "AWS", "budget_usd": 500,
    }
    requirements.update(overrides)
    return requirements


def test_recommendations_are_ordered_explainable_and_not_live_prices() -> None:
    result = build_recommendations(base_requirements())
    assert [item["tier"] for item in result] == ["Cost-optimized", "Balanced", "Performance-optimized"]
    assert result[0]["estimated_cost_usd"] < result[1]["estimated_cost_usd"] < result[2]["estimated_cost_usd"]
    assert all(item["fits_budget"] for item in result)
    assert all(item["rule_version"] == "resource-fit-rules/1.0.0" for item in result)
    assert all("not current provider pricing" in item["cost_basis"] for item in result)
    assert all(item["data_source"] and item["rationale"] and item["confidence"] for item in result)


def test_budget_overrun_is_explicit_and_not_actionable() -> None:
    result = build_recommendations(base_requirements(budget_usd=0.5))
    assert all(not item["fits_budget"] for item in result)
    assert all(any("Exceeds" in reason for reason in item["rationale"]) for item in result)


def test_traditional_ml_does_not_get_an_assumed_gpu() -> None:
    analysis = analyze_workload(base_requirements())
    assert analysis["demand"]["gpu_count"] == 0
    assert analysis["predictive_model_ready"] is False


def test_low_memory_or_tight_latency_creates_review_risks() -> None:
    analysis = analyze_workload(base_requirements(dataset_gb=100, memory_gb=8, latency_ms=50, inference_rps=200))
    assert len(analysis["bottlenecks"]) >= 2
    assert analysis["data_source"] == "user-provided requirements"


def test_provider_adapter_preview_never_creates_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    adapter = AWSAdapter()
    status = adapter.status()
    assert status.configured is False
    assert status.live_actions_enabled is False
    assert "AWS_SECRET_ACCESS_KEY" in status.missing_fields
    plan = adapter.build_plan_preview(workload_id="workload-demo", configuration={"cpu_cores": 4})
    assert plan["real_resources_created"] is False
    with pytest.raises(ProviderNotConfigured):
        adapter.provision(approved=True)


def test_preview_jwt_requires_valid_app_and_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    secret, app_id = "test-only-secret", "astra-test-project"
    monkeypatch.setenv("MANUS_JWT_SECRET", secret)
    monkeypatch.setenv("MANUS_PROJECT_ID", app_id)
    claims = {"openId": "owner-123", "appId": app_id, "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    token = jwt.encode(claims, secret, algorithm="HS256")
    assert _preview_identity(token) == "owner-123"
    other_app = jwt.encode({**claims, "appId": "another-project"}, secret, algorithm="HS256")
    assert _preview_identity(other_app) is None
    expired = jwt.encode({**claims, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, secret, algorithm="HS256")
    assert _preview_identity(expired) is None


def test_managed_mysql_json_tls_options_are_translated_for_pymysql() -> None:
    url, connect_args = database_engine_parts("mysql://user:password@db.example.test/app?ssl=%7B%22rejectUnauthorized%22%3Atrue%7D")
    assert url.drivername == "mysql+pymysql"
    assert "ssl" not in url.query
    assert connect_args["ssl"]["verify_mode"] == "required"
    assert connect_args["ssl"]["check_hostname"] is True
    assert bool(connect_args["ssl"].get("ca") or connect_args["ssl"].get("capath"))
