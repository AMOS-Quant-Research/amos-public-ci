from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SUPPORTED_PROVIDERS = {
    "github_actions", "cloudflare", "nvidia_nim", "free_vm", "free_gpu", "ctrader_cloud",
}
SUPPORTED_CAPABILITIES = {
    "control_api", "notification", "validation", "scheduled_job", "ai_analysis",
    "batch_research", "execution_relay", "managed_bot_runtime", "runtime_status",
}


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    enabled: bool
    purpose: tuple[str, ...]
    delegated_role: str
    secret_refs: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ProviderConfig":
        name = str(value["name"])
        if name not in SUPPORTED_PROVIDERS:
            raise ValueError(f"unsupported provider: {name}")
        enabled = value.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError("provider enabled must be a JSON boolean")
        return cls(
            name=name,
            enabled=enabled,
            purpose=tuple(value.get("purpose", [])),
            delegated_role=str(value.get("delegated_role", "none")),
            secret_refs=tuple(value.get("secret_refs", [])),
        )


@dataclass(frozen=True)
class TenantConfig:
    tenant_id: str
    display_name: str
    execution_mode: str
    owner_controls: tuple[str, ...]
    providers: tuple[ProviderConfig, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TenantConfig":
        tenant_id = str(value["tenant_id"])
        if not tenant_id.replace("-", "").isalnum():
            raise ValueError("tenant_id must be alphanumeric with optional hyphens")
        mode = str(value.get("execution_mode", "shadow"))
        if mode not in {"research", "shadow", "demo", "live"}:
            raise ValueError("execution_mode must be research, shadow, demo, or live")
        providers = tuple(ProviderConfig.from_dict(p) for p in value.get("providers", []))
        if not providers:
            raise ValueError("at least one provider is required")
        names = [p.name for p in providers]
        if len(names) != len(set(names)):
            raise ValueError("providers may only occur once")
        return cls(
            tenant_id=tenant_id,
            display_name=str(value.get("display_name", tenant_id)),
            execution_mode=mode,
            owner_controls=tuple(value.get("owner_controls", ["revoke_access", "emergency_stop"])),
            providers=providers,
        )


@dataclass(frozen=True)
class MeshRequest:
    """A provider-neutral request accepted by AMOS Mesh."""

    capability: str
    tenant_id: str
    continuous: bool = False

    def __post_init__(self) -> None:
        if self.capability not in SUPPORTED_CAPABILITIES:
            raise ValueError(f"unsupported capability: {self.capability}")
