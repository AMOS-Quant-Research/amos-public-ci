from __future__ import annotations

from dataclasses import dataclass

from .models import ProviderConfig


@dataclass(frozen=True)
class ProvisionStep:
    provider: str
    action: str
    detail: str
    requires_owner_approval: bool = True


class ProviderAdapter:
    provider_name = "base"

    def plan(self, config: ProviderConfig) -> list[ProvisionStep]:
        raise NotImplementedError


class GitHubActionsAdapter(ProviderAdapter):
    provider_name = "github_actions"

    def plan(self, config: ProviderConfig) -> list[ProvisionStep]:
        return [
            ProvisionStep(self.provider_name, "install-github-app", "Grant repository-scoped workflow and commit-status permissions."),
            ProvisionStep(self.provider_name, "create-environment", "Create a tenant environment and attach approved secret references."),
        ]


class CloudflareAdapter(ProviderAdapter):
    provider_name = "cloudflare"

    def plan(self, config: ProviderConfig) -> list[ProvisionStep]:
        return [
            ProvisionStep(self.provider_name, "create-api-token", "Use a scoped token for Worker deployment and selected routes only."),
            ProvisionStep(self.provider_name, "deploy-control-worker", "Deploy the signed control and notification endpoint."),
        ]


class NvidiaNimAdapter(ProviderAdapter):
    provider_name = "nvidia_nim"

    def plan(self, config: ProviderConfig) -> list[ProvisionStep]:
        return [ProvisionStep(self.provider_name, "register-secret-reference", "Reference the customer-owned NIM API secret without exporting it.")]


class FreeVmAdapter(ProviderAdapter):
    provider_name = "free_vm"

    def plan(self, config: ProviderConfig) -> list[ProvisionStep]:
        return [
            ProvisionStep(self.provider_name, "enroll-runner", "Install the outbound-only AMOS Mesh Agent in the approved VM."),
            ProvisionStep(self.provider_name, "apply-stop-policy", "Configure heartbeat loss and owner emergency-stop behavior."),
        ]


class FreeGpuAdapter(ProviderAdapter):
    provider_name = "free_gpu"

    def plan(self, config: ProviderConfig) -> list[ProvisionStep]:
        return [ProvisionStep(self.provider_name, "register-batch-profile", "Register non-continuous research jobs; do not depend on this provider for continuous execution.")]


class CTraderCloudAdapter(ProviderAdapter):
    """Plans only customer-controlled cBot Cloud enrollment.

    AMOS never receives a cTrader password, trading PIN, withdrawal right, or
    discretionary authority. The owner starts, stops, and funds the cBot in
    their own cTrader account.
    """

    provider_name = "ctrader_cloud"

    def plan(self, config: ProviderConfig) -> list[ProvisionStep]:
        return [
            ProvisionStep(self.provider_name, "verify-broker-availability", "Confirm that the customer's broker account supports cTrader Cloud cBot execution."),
            ProvisionStep(self.provider_name, "deliver-protected-cbot", "Deliver the versioned AMOS cBot package and default risk profile to the customer account."),
            ProvisionStep(self.provider_name, "owner-starts-cloud-instance", "Customer selects the account, symbol, and parameters, then starts or stops the Cloud instance."),
            ProvisionStep(self.provider_name, "register-runtime-status", "Register health and version status only; do not collect credentials or trading authority."),
        ]


ADAPTERS: dict[str, ProviderAdapter] = {
    adapter.provider_name: adapter
    for adapter in (
        GitHubActionsAdapter(), CloudflareAdapter(), NvidiaNimAdapter(), FreeVmAdapter(),
        FreeGpuAdapter(), CTraderCloudAdapter(),
    )
}
