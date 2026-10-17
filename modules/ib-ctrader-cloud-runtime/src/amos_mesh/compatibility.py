"""Provider-neutral capability routing for AMOS Mesh.

This clean-room implementation borrows only the compatibility-layer pattern:
callers ask for a capability and the resolver selects an enabled backend.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .models import MeshRequest, TenantConfig


CAPABILITY_MATRIX: dict[str, tuple[str, ...]] = {
    "control_api": ("cloudflare",),
    "notification": ("cloudflare", "github_actions"),
    "validation": ("github_actions",),
    "scheduled_job": ("github_actions",),
    "ai_analysis": ("nvidia_nim",),
    "batch_research": ("free_gpu", "github_actions"),
    "execution_relay": ("free_vm",),
    "managed_bot_runtime": ("ctrader_cloud", "free_vm"),
    "runtime_status": ("ctrader_cloud", "cloudflare", "github_actions"),
}


@dataclass(frozen=True)
class Route:
    capability: str
    provider: str
    continuous: bool
    fallback_providers: tuple[str, ...]
    safety_note: str | None = None


class MeshResolver:
    """Resolves AMOS capabilities while keeping callers vendor-neutral."""

    def resolve(self, tenant: TenantConfig, request: MeshRequest) -> Route:
        if request.tenant_id != tenant.tenant_id:
            raise ValueError("request tenant_id does not match tenant configuration")
        enabled = {item.name for item in tenant.providers if item.enabled}
        candidates = [name for name in CAPABILITY_MATRIX[request.capability] if name in enabled]
        if not candidates:
            raise ValueError(f"no enabled backend for capability '{request.capability}'")
        if request.continuous and request.capability not in {"execution_relay", "managed_bot_runtime"}:
            raise ValueError("continuous requests are allowed only for execution_relay or managed_bot_runtime")
        return Route(
            capability=request.capability,
            provider=candidates[0],
            continuous=request.continuous,
            fallback_providers=tuple(candidates[1:]),
            safety_note=("Free-capacity loss must trigger safe-stop; availability is not guaranteed."
                         if request.continuous else None),
        )

    def resolve_dict(self, tenant: TenantConfig, request: MeshRequest) -> dict[str, object]:
        return asdict(self.resolve(tenant, request))
