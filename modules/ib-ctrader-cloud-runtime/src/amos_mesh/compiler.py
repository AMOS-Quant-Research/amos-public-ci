from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import TenantConfig
from .compatibility import CAPABILITY_MATRIX, MeshResolver
from .providers import ADAPTERS, ProvisionStep


class MeshCompiler:
    """Compiles a customer-owned multi-cloud profile into an approval-first plan."""

    def load(self, path: str | Path) -> TenantConfig:
        with Path(path).open(encoding="utf-8") as handle:
            return TenantConfig.from_dict(json.load(handle))

    def plan(self, tenant: TenantConfig) -> dict[str, Any]:
        steps: list[ProvisionStep] = []
        active = [provider for provider in tenant.providers if provider.enabled]
        for provider in active:
            steps.extend(ADAPTERS[provider.name].plan(provider))
        return {
            "tenant_id": tenant.tenant_id,
            "display_name": tenant.display_name,
            "execution_mode": tenant.execution_mode,
            "owner_controls": list(tenant.owner_controls),
            "active_providers": [provider.name for provider in active],
            "capability_matrix": {
                capability: [provider for provider in providers if provider in {item.name for item in active}]
                for capability, providers in CAPABILITY_MATRIX.items()
            },
            "steps": [asdict(step) for step in steps],
            "safety": {
                "customer_owns_accounts": True,
                "credentials_exported_to_amos": False,
                "approval_required_before_apply": True,
                "automatic_trading_decisions": False,
                "customer_retains_start_stop_and_funding_control": True,
                "no_customer_password_or_withdrawal_authority": True,
            },
        }

    def route(self, tenant: TenantConfig, capability: str, *, continuous: bool = False) -> dict[str, Any]:
        from .models import MeshRequest

        return MeshResolver().resolve_dict(
            tenant, MeshRequest(capability=capability, tenant_id=tenant.tenant_id, continuous=continuous)
        )
