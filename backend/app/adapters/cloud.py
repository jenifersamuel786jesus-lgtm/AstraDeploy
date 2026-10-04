from __future__ import annotations

import os
from dataclasses import dataclass
from typing import ClassVar


class ProviderNotConfigured(RuntimeError):
    """Raised when a live provider operation is requested without protected setup."""


@dataclass(frozen=True)
class ProviderStatus:
    provider: str
    configured: bool
    missing_fields: tuple[str, ...]
    live_actions_enabled: bool = False


class CloudAdapter:
    name: ClassVar[str]
    credential_keys: ClassVar[tuple[str, ...]]

    def status(self) -> ProviderStatus:
        missing = tuple(key for key in self.credential_keys if not os.getenv(key))
        return ProviderStatus(provider=self.name, configured=not missing, missing_fields=missing)

    def build_plan_preview(self, *, workload_id: str, configuration: dict[str, object]) -> dict[str, object]:
        """Render metadata only; never creates, updates or deletes provider resources."""
        return {
            "provider": self.name,
            "workload_id": workload_id,
            "configuration": configuration,
            "state": "review-only",
            "real_resources_created": False,
            "required_before_apply": ["validated provider integration", "least-privilege permissions", "explicit operator approval"],
        }

    def provision(self, *, approved: bool = False) -> None:
        """Live apply is deliberately unavailable in this demo implementation."""
        status = self.status()
        if not status.configured:
            raise ProviderNotConfigured(f"{self.name} is not configured; missing {', '.join(status.missing_fields)}.")
        if not approved:
            raise ProviderNotConfigured(f"{self.name} live provisioning requires an explicit approval workflow.")
        raise ProviderNotConfigured(f"{self.name} has credentials but no live provisioning adapter is enabled in this build.")


class AWSAdapter(CloudAdapter):
    name = "AWS"
    credential_keys = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION")


class AzureAdapter(CloudAdapter):
    name = "Microsoft Azure"
    credential_keys = ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_SUBSCRIPTION_ID")


class GCPAdapter(CloudAdapter):
    name = "Google Cloud"
    credential_keys = ("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT")


def provider_adapters() -> tuple[CloudAdapter, ...]:
    return AWSAdapter(), AzureAdapter(), GCPAdapter()
