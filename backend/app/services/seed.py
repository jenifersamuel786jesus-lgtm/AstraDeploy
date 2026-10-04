from __future__ import annotations
from typing import Any
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from backend.app.models.entities import DemoRecord, Project, Workload

SAMPLE_WORKLOADS = [
    {"name": "Vision defect classifier", "task_type": "Computer vision training", "framework": "PyTorch", "status": "Ready", "requirements": {"dataset_gb": 68, "training_samples": 920000, "training_hours": 9, "cpu_cores": 8, "memory_gb": 32, "gpu_count": 1, "storage_gb": 140, "latency_ms": 180, "inference_rps": 40, "provider": "AWS", "budget_usd": 90}},
    {"name": "Demand forecast v3", "task_type": "Traditional ML training", "framework": "XGBoost", "status": "Analyzed", "requirements": {"dataset_gb": 24, "training_samples": 430000, "training_hours": 3.5, "cpu_cores": 8, "memory_gb": 24, "gpu_count": 0, "storage_gb": 64, "latency_ms": 250, "provider": "GCP", "budget_usd": 45}},
    {"name": "Support intent API", "task_type": "NLP inference", "framework": "ONNX Runtime", "status": "Running", "requirements": {"dataset_gb": 12, "training_samples": 180000, "training_hours": 2, "cpu_cores": 4, "memory_gb": 16, "gpu_count": 0, "storage_gb": 48, "latency_ms": 95, "inference_rps": 210, "provider": "Azure", "budget_usd": 65}},
    {"name": "Nightly embeddings batch", "task_type": "Batch prediction", "framework": "PyTorch", "status": "Ready", "requirements": {"dataset_gb": 120, "training_samples": 1300000, "training_hours": 5, "cpu_cores": 12, "memory_gb": 48, "gpu_count": 1, "storage_gb": 250, "latency_ms": 500, "provider": "AWS", "budget_usd": 110}},
]

SAMPLE_RECORDS: dict[str, list[dict[str, Any]]] = {
    "pipelines": [
        {"name": "Vision model release", "project": "ML Platform", "status": "Running", "progress": 68, "stages": ["Ingest", "Validate", "Features", "Train", "Evaluate", "Register", "Deploy"], "updated": "4 min ago", "mode": "demo"},
        {"name": "Demand forecast refresh", "project": "ML Platform", "status": "Succeeded", "progress": 100, "stages": ["Ingest", "Validate", "Train", "Evaluate", "Register"], "updated": "2 hr ago", "mode": "demo"},
        {"name": "Embedding refresh", "project": "ML Platform", "status": "Queued", "progress": 0, "stages": ["Ingest", "Validate", "Train", "Register"], "updated": "Yesterday", "mode": "demo"},
    ],
    "models": [
        {"name": "vision-defect-resnet", "version": "v2.4.1", "framework": "PyTorch", "stage": "Production", "accuracy": 0.964, "updated": "Today", "mode": "demo"},
        {"name": "demand-forecast-xgb", "version": "v3.1.0", "framework": "XGBoost", "stage": "Staging", "accuracy": 0.918, "updated": "Yesterday", "mode": "demo"},
        {"name": "support-intent-onnx", "version": "v1.8.2", "framework": "ONNX", "stage": "Production", "accuracy": 0.941, "updated": "Sep 28", "mode": "demo"},
    ],
    "experiments": [
        {"name": "vision-resnet-sweep-07", "model": "vision-defect-resnet", "run": "run-184", "metric": "F1 0.964", "duration": "1h 42m", "status": "Complete", "mode": "demo"},
        {"name": "demand-xgb-depth", "model": "demand-forecast-xgb", "run": "run-179", "metric": "MAPE 8.2%", "duration": "18m", "status": "Complete", "mode": "demo"},
        {"name": "intent-distillation", "model": "support-intent-onnx", "run": "run-172", "metric": "F1 0.941", "duration": "32m", "status": "Complete", "mode": "demo"},
    ],
    "deployments": [
        {"name": "support-intent-api", "model": "support-intent-onnx:v1.8.2", "environment": "Production", "state": "Running", "provider": "Demo adapter", "endpoint": "demo://support-intent", "latency_ms": 82, "requests": 1240, "mode": "demo"},
        {"name": "vision-edge-staging", "model": "vision-defect-resnet:v2.4.1", "environment": "Staging", "state": "Running", "provider": "Demo adapter", "endpoint": "demo://vision-edge", "latency_ms": 146, "requests": 318, "mode": "demo"},
    ],
    "alerts": [
        {"title": "Budget at 75%", "description": "Vision training project reached 76% of its illustrative monthly budget.", "severity": "Warning", "status": "Open", "time": "12 min ago", "source": "Demo budget policy", "mode": "demo"},
        {"title": "Inference latency elevated", "description": "Support intent demo endpoint crossed its 90 ms target in one sample window.", "severity": "Warning", "status": "Acknowledged", "time": "1 hr ago", "source": "Demo telemetry", "mode": "demo"},
        {"title": "Pipeline stage retried", "description": "Vision model evaluation stage recovered after a simulated retry.", "severity": "Info", "status": "Resolved", "time": "Yesterday", "source": "Demo pipeline", "mode": "demo"},
    ],
    "budgets": [
        {"name": "ML Platform monthly", "scope": "Organization", "limit_usd": 2800, "spent_usd": 1840, "thresholds": [50, 75, 90, 100], "mode": "demo"},
        {"name": "Vision training", "scope": "Project", "limit_usd": 900, "spent_usd": 684, "thresholds": [50, 75, 90, 100], "mode": "demo"},
    ],
    "costs": [
        {"label": "Compute", "amount_usd": 1126, "change_pct": 4.2, "mode": "demo-estimate"},
        {"label": "Storage", "amount_usd": 384, "change_pct": -2.1, "mode": "demo-estimate"},
        {"label": "Inference", "amount_usd": 330, "change_pct": 8.4, "mode": "demo-estimate"},
    ],
    "optimizations": [
        {"title": "Right-size forecast worker", "target": "Demand forecast v3", "current": "8 vCPU · 24 GB", "recommended": "4 vCPU · 16 GB", "monthly_before_usd": 248, "monthly_after_usd": 162, "saving_pct": 35, "risk": "Low", "status": "Open", "mode": "demo-estimate"},
        {"title": "Schedule idle GPU pool", "target": "Nightly embeddings batch", "current": "GPU reserved 24/7", "recommended": "Queue with scheduled warm-up", "monthly_before_usd": 912, "monthly_after_usd": 535, "saving_pct": 41, "risk": "Medium", "status": "Open", "mode": "demo-estimate"},
        {"title": "Tune API autoscaling", "target": "Support intent API", "current": "4–16 replicas", "recommended": "2–10 replicas, 65% CPU target", "monthly_before_usd": 460, "monthly_after_usd": 398, "saving_pct": 13, "risk": "Low", "status": "Applied (simulated)", "mode": "demo-estimate"},
    ],
    "infrastructure": [
        {"name": "ml-training-pool", "type": "Kubernetes node pool", "provider": "Not connected", "region": "—", "state": "Template only", "mode": "demo"},
        {"name": "model-artifacts", "type": "Object storage", "provider": "Not connected", "region": "—", "state": "Template only", "mode": "demo"},
    ],
    "metrics": [
        {"label": "CPU", "current": 63, "unit": "%", "trend": "+4.2%", "mode": "demo"},
        {"label": "Memory", "current": 71, "unit": "%", "trend": "+1.8%", "mode": "demo"},
        {"label": "GPU", "current": 48, "unit": "%", "trend": "−6.1%", "mode": "demo"},
        {"label": "Inference p95", "current": 82, "unit": "ms", "trend": "−3.4%", "mode": "demo"},
    ],
    "activity": [
        {"title": "Resource plan reviewed", "description": "Balanced profile · vision defect classifier", "time": "8 min ago", "mode": "demo"},
        {"title": "Model registered", "description": "support-intent-onnx v1.8.2 · Production", "time": "36 min ago", "mode": "demo"},
        {"title": "Optimization identified", "description": "Demand forecast worker · potential 35% estimate", "time": "2 hr ago", "mode": "demo"},
    ],
    "integrations": [
        {"name": "AWS", "category": "Cloud provider", "status": "Not connected", "capability": "Provisioning and billing"},
        {"name": "Microsoft Azure", "category": "Cloud provider", "status": "Not connected", "capability": "Provisioning and billing"},
        {"name": "Google Cloud", "category": "Cloud provider", "status": "Not connected", "capability": "Provisioning and billing"},
        {"name": "Kubernetes / Terraform", "category": "Infrastructure", "status": "Template only", "capability": "Plan preview and orchestration"},
        {"name": "MLflow", "category": "MLOps", "status": "Not connected", "capability": "Runs and model tracking"},
        {"name": "Prometheus / Grafana", "category": "Observability", "status": "Not connected", "capability": "Live metrics and alerting"},
    ],
}


def seed_demo_workspace(db: Session, organization_id: str) -> None:
    count = db.scalar(select(func.count()).select_from(Workload).where(Workload.organization_id == organization_id)) or 0
    if count:
        return
    project = db.scalar(select(Project).where(Project.organization_id == organization_id))
    project_id = project.id if project else None
    for item in SAMPLE_WORKLOADS:
        db.add(Workload(organization_id=organization_id, project_id=project_id, is_demo=True, **item))
    for kind, rows in SAMPLE_RECORDS.items():
        for payload in rows:
            db.add(DemoRecord(organization_id=organization_id, kind=kind, payload=payload, is_demo=True))
    db.commit()
