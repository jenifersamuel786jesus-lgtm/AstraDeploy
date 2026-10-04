from __future__ import annotations
from typing import Any

GPU_TASKS = {"computer vision", "deep learning", "natural language processing"}
GPU_RATE_PER_HOUR = 2.60  # Illustrative demo price only; not a live provider quote.
CPU_RATE_PER_HOUR = 0.035
MEMORY_RATE_PER_GB_HOUR = 0.004
STORAGE_RATE_PER_GB_MONTH = 0.085


def analyze_workload(requirements: dict[str, Any]) -> dict[str, Any]:
    samples = max(1, int(requirements.get("training_samples") or 250_000))
    data_gb = max(1.0, float(requirements.get("dataset_gb") or 48))
    task = str(requirements.get("task_type") or "Training")
    cpu = max(2, int(requirements.get("cpu_cores") or min(32, 2 + samples // 250_000)))
    memory = max(4, int(requirements.get("memory_gb") or min(128, 8 + data_gb * 0.35)))
    gpu = int(requirements.get("gpu_count") or (1 if any(x in task.lower() for x in GPU_TASKS) else 0))
    storage = max(50, int(requirements.get("storage_gb") or data_gb * 2))
    latency = int(requirements.get("latency_ms") or 250)
    inference = int(requirements.get("inference_rps") or 0)
    risks: list[str] = []
    if memory < data_gb * 0.5:
        risks.append("Memory may constrain preprocessing; profile peak working-set size before production.")
    if latency < 100 and inference > 0:
        risks.append("A sub-100 ms target needs representative load testing and a region-level latency check.")
    if gpu == 0 and any(x in task.lower() for x in {"computer vision", "deep learning", "natural language processing"}):
        risks.append("This task often benefits from a GPU; the current input explicitly requests none.")
    return {
        "classification": task,
        "demand": {"cpu_cores": cpu, "memory_gb": round(memory), "gpu_count": gpu, "storage_gb": round(storage)},
        "profile": {"dataset_gb": data_gb, "training_samples": samples, "latency_target_ms": latency, "inference_rps": inference},
        "bottlenecks": risks or ["No hard bottleneck inferred from supplied requirements; validate with representative telemetry."],
        "method": "transparent workload rules v1.0",
        "data_source": "user-provided requirements",
        "predictive_model_ready": False,
    }


def build_recommendations(requirements: dict[str, Any]) -> list[dict[str, Any]]:
    analysis = analyze_workload(requirements)
    demand = analysis["demand"]
    training_hours = max(0.5, float(requirements.get("training_hours") or 8))
    data_gb = float(analysis["profile"]["dataset_gb"])
    provider = str(requirements.get("provider") or "AWS")
    budget = float(requirements.get("budget_usd") or 0)
    profiles = [
        ("Cost-optimized", 0.72, 0.78, "Lower-cost compute profile; longer runtime or lower headroom may result."),
        ("Balanced", 1.0, 1.0, "Balances resource fit and estimated cost under the provided assumptions."),
        ("Performance-optimized", 1.7, 1.35, "Adds capacity and headroom; highest illustrative spend of these options."),
    ]
    choices: list[dict[str, Any]] = []
    for tier, resource_factor, speed_factor, tradeoff in profiles:
        cpu = max(2, round(demand["cpu_cores"] * resource_factor))
        memory = max(4, round(demand["memory_gb"] * resource_factor))
        gpu = demand["gpu_count"] if resource_factor < 1 else max(demand["gpu_count"], 1 if demand["gpu_count"] else 0)
        hourly = cpu * CPU_RATE_PER_HOUR + memory * MEMORY_RATE_PER_GB_HOUR + gpu * GPU_RATE_PER_HOUR
        cost = round(hourly * training_hours + data_gb * STORAGE_RATE_PER_GB_MONTH, 2)
        reasons = [
            f"Sized from {analysis['profile']['training_samples']:,} training samples and a {data_gb:g} GB dataset.",
            f"Targets {demand['cpu_cores']} vCPU / {demand['memory_gb']} GB RAM baseline; candidate scales by {resource_factor:.2f}×.",
            tradeoff,
        ]
        fits_budget = budget <= 0 or cost <= budget
        if not fits_budget:
            reasons.append(f"Exceeds the entered per-run budget of ${budget:,.0f}; do not proceed without adjustment/approval.")
        choices.append({
            "tier": tier,
            "provider": provider,
            "instance": f"{provider.lower()}-general-purpose-{max(cpu, 2)}c{memory}m" + ("-1gpu" if gpu else ""),
            "cpu_cores": cpu,
            "memory_gb": memory,
            "gpu_count": gpu,
            "gpu_type": "T4-class (illustrative)" if gpu else None,
            "storage_gb": demand["storage_gb"],
            "runtime_hours_estimate": round(training_hours / speed_factor, 1),
            "estimated_cost_usd": cost,
            "cost_basis": "Illustrative demo rate card; not current provider pricing.",
            "architecture": "Containerized training job; object storage for artifacts; bounded autoscaling at inference.",
            "autoscaling": {"min_replicas": 1, "max_replicas": 4 if tier != "Performance-optimized" else 8, "target_cpu_percent": 65},
            "fits_budget": fits_budget,
            "assumptions": ["Single region; USD; illustrative compute/storage rates; no egress, taxes, discounts or managed-service fees."],
            "rationale": reasons,
            "confidence": "Rule-based fit; low-to-moderate until historical telemetry exists.",
            "data_source": "User requirements + AstraDeploy illustrative rate card",
            "rule_version": "resource-fit-rules/1.0.0",
        })
    return choices
