from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


class OAuthStartInput(BaseModel):
    redirect_uri: str = Field(min_length=1, max_length=2048)


class WorkloadInput(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    project_id: str | None = None
    task_type: str = Field(default="Training", max_length=80)
    framework: str = Field(default="PyTorch", max_length=80)
    dataset_gb: float = Field(default=48, ge=0.1, le=1000000)
    training_samples: int = Field(default=250000, ge=1, le=10_000_000_000)
    training_hours: float = Field(default=8, ge=0.1, le=8760)
    cpu_cores: int = Field(default=4, ge=1, le=1024)
    memory_gb: int = Field(default=16, ge=1, le=16384)
    gpu_count: int = Field(default=0, ge=0, le=128)
    storage_gb: int = Field(default=100, ge=1, le=10_000_000)
    latency_ms: int = Field(default=250, ge=1, le=600_000)
    inference_rps: int = Field(default=0, ge=0, le=10_000_000)
    provider: str = Field(default="AWS", max_length=32)
    budget_usd: float = Field(default=0, ge=0, le=100_000_000)
    availability: str = Field(default="Standard", max_length=32)

    @field_validator("provider")
    @classmethod
    def provider_choice(cls, value: str) -> str:
        allowed = {"AWS", "Azure", "GCP", "No preference"}
        if value not in allowed:
            raise ValueError("Provider must be AWS, Azure, GCP or No preference.")
        return value

    def requirements(self) -> dict[str, Any]:
        return self.model_dump(exclude={"name", "project_id", "task_type", "framework"})


class ProjectInput(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    description: str = Field(default="", max_length=1000)


class RoleUpdate(BaseModel):
    role: Literal["Admin", "ML/DevOps Engineer", "Data Scientist/Developer", "Viewer"]


class ReportInput(BaseModel):
    report_type: Literal[
        "Workload analysis",
        "Resource recommendations",
        "Cost optimization",
        "Deployment summary",
        "Pipeline execution",
        "Audit activity",
    ] = "Workload analysis"


class RecordCreate(BaseModel):
    kind: Literal["pipelines", "models", "experiments", "alerts", "budgets", "deployments", "reports"]
    payload: dict[str, Any]


class ActionInput(BaseModel):
    action: Literal["run_pipeline", "acknowledge_alert", "resolve_alert", "apply_optimization", "dismiss_optimization", "create_deployment", "create_budget"]
    record_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
