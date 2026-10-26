"""Standard-library tests for OpenCode fallback diagnostics."""

import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "scripts" / "classify_opencode_error.py"
spec = importlib.util.spec_from_file_location("opencode_classifier", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ClassifierTests(unittest.TestCase):
    def test_mobile_403(self):
        result = module.classify("GET http://desktop-eoslnkl:8435/session/status → 403 forbidden")
        self.assertEqual(result["category"], "access_denied")
        self.assertEqual(result["http_status"], "403")
        self.assertFalse(result["root_cause_verified"])

    def test_401(self):
        self.assertEqual(module.classify("HTTP 401 Unauthorized")["category"], "access_denied")

    def test_429(self):
        self.assertEqual(module.classify("429 Too Many Requests")["category"], "rate_or_quota")

    def test_runner(self):
        self.assertEqual(module.classify("GitHub runner offline")["category"], "runner_unavailable")

    def test_permissions(self):
        self.assertEqual(module.classify("Resource not accessible by integration")["category"], "github_permission")

    def test_model(self):
        self.assertEqual(module.classify("model not found")["category"], "model_unavailable")

    def test_503(self):
        self.assertEqual(module.classify("HTTP 503 Service Unavailable")["category"], "upstream_failure")

    def test_unknown(self):
        self.assertEqual(module.classify("something happened")["category"], "unclassified")

    def test_no_message_echo(self):
        self.assertNotIn("topsecret", str(module.classify("Bearer topsecret 403 Forbidden")))

    def test_non_string(self):
        with self.assertRaises(TypeError):
            module.classify(None)


if __name__ == "__main__":
    unittest.main()
