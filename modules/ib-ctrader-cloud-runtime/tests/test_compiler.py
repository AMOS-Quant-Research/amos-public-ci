import unittest
from pathlib import Path

from amos_mesh.compatibility import MeshResolver
from amos_mesh.compiler import MeshCompiler
from amos_mesh.models import MeshRequest, TenantConfig


class MeshCompilerTests(unittest.TestCase):
    def test_demo_plan_requires_approval(self):
        root = Path(__file__).parents[1]
        plan = MeshCompiler().plan(MeshCompiler().load(root / "examples" / "tenant-demo.json"))
        self.assertTrue(plan["safety"]["approval_required_before_apply"])
        self.assertIn("cloudflare", plan["active_providers"])
        self.assertIn("ctrader_cloud", plan["active_providers"])
        self.assertGreaterEqual(len(plan["steps"]), 9)

    def test_unknown_provider_is_rejected(self):
        with self.assertRaises(ValueError):
            TenantConfig.from_dict({"tenant_id": "bad", "providers": [{"name": "unknown"}]})

    def test_provider_enabled_must_be_boolean(self):
        with self.assertRaises(ValueError):
            TenantConfig.from_dict({
                "tenant_id": "bad",
                "providers": [{"name": "cloudflare", "enabled": "false"}],
            })

    def test_capability_is_routed_without_provider_in_the_request(self):
        root = Path(__file__).parents[1]
        tenant = MeshCompiler().load(root / "examples" / "tenant-demo.json")
        route = MeshCompiler().route(tenant, "notification")
        self.assertEqual(route["provider"], "cloudflare")
        self.assertEqual(route["capability"], "notification")

    def test_disabled_provider_is_not_routed(self):
        tenant = TenantConfig.from_dict({
            "tenant_id": "tenant-a",
            "providers": [
                {"name": "cloudflare", "enabled": False},
                {"name": "github_actions", "enabled": True},
            ],
        })
        route = MeshResolver().resolve(tenant, MeshRequest("notification", "tenant-a"))
        self.assertEqual(route.provider, "github_actions")

    def test_resolver_rejects_cross_tenant_request(self):
        tenant = TenantConfig.from_dict({
            "tenant_id": "tenant-a",
            "providers": [{"name": "cloudflare"}],
        })
        with self.assertRaises(ValueError):
            MeshResolver().resolve(tenant, MeshRequest("notification", "tenant-b"))

    def test_continuous_work_is_restricted_to_relay(self):
        root = Path(__file__).parents[1]
        tenant = MeshCompiler().load(root / "examples" / "tenant-demo.json")
        with self.assertRaises(ValueError):
            MeshCompiler().route(tenant, "ai_analysis", continuous=True)

    def test_ctrader_is_the_vpsless_runtime_when_enabled(self):
        root = Path(__file__).parents[1]
        tenant = MeshCompiler().load(root / "examples" / "tenant-demo.json")
        route = MeshCompiler().route(tenant, "managed_bot_runtime", continuous=True)
        self.assertEqual(route["provider"], "ctrader_cloud")
