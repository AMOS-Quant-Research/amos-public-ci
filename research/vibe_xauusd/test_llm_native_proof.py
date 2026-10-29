import json
from pathlib import Path
import tempfile
import unittest
from verify_llm_native_proof import verify


class ProofTests(unittest.TestCase):
    def check(self, proposal, ledger, summary):
        with tempfile.TemporaryDirectory() as tmp:
            p = [Path(tmp)/f"{i}.json" for i in range(3)]
            for path, data in zip(p, (proposal, ledger, summary)):
                path.write_text(json.dumps(data))
            return verify(*p)

    def test_heuristic_does_not_pass(self):
        result = self.check(
            {"contract": "amos.ae.proposal-evidence.v1", "generator": "metric_guided_deterministic",
             "llm_hypothesis_generation_verified": False, "nim_status": "credential_not_configured"},
            {"contract": "amos.ae.autonomous-ledger.v1", "completed": []},
            {"contract": "amos.ae.autonomous-run.v1", "new_results": []})
        self.assertEqual(result["verdict"], "BLOCKED")

    def test_mock_evidence_matching(self):
        plan = {"lambda": 1.25, "momentum": 6, "lookback": 90}
        candidate = {"candidate_key": "mock-sha", "plan": plan, "returncode": 0,
                     "native_fills": 8, "live_trading": False}
        result = self.check(
            {"contract": "amos.ae.proposal-evidence.v1", "generator": "openrouter_free",
             "ai_provider_status": "openrouter_free_validated_json", "llm_hypothesis_generation_verified": True,
             "candidate_parameters": [plan], "llm_generated_candidate_count": 1},
            {"contract": "amos.ae.autonomous-ledger.v1", "completed": [candidate]},
            {"contract": "amos.ae.autonomous-run.v1", "new_results": [candidate]})
        self.assertEqual(result["verdict"], "PASS")

    def test_nvidia_candidate_native_fill_matches(self):
        plan = {"lambda": 1.75, "momentum": 7, "lookback": 110}
        candidate = {"candidate_key": "mock-nim-sha", "plan": plan, "returncode": 0,
                     "native_fills": 3, "live_trading": False}
        result = self.check(
            {"contract": "amos.ae.proposal-evidence.v1", "generator": "nvidia_nim",
             "nim_status": "nim_validated_json",
             "ai_provider_status": "nvidia_nim_validated_json",
             "llm_hypothesis_generation_verified": True,
             "candidate_parameters": [plan], "llm_generated_candidate_count": 1},
            {"contract": "amos.ae.autonomous-ledger.v1", "completed": [candidate]},
            {"contract": "amos.ae.autonomous-run.v1", "new_results": [candidate]})
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["matched_candidate_keys"], ["mock-nim-sha"])

    def test_nvidia_schema_failure_is_reported_and_blocked(self):
        result = self.check(
            {"contract": "amos.ae.proposal-evidence.v1",
             "generator": "metric_guided_deterministic",
             "nim_status": "nim_invalid_response_schema",
             "ai_provider_status": "openrouter_free_not_configured",
             "llm_hypothesis_generation_verified": False},
            {"contract": "amos.ae.autonomous-ledger.v1", "completed": []},
            {"contract": "amos.ae.autonomous-run.v1", "new_results": []})
        self.assertEqual(result["verdict"], "BLOCKED")
        self.assertIn("nim_invalid_response_schema", result["reason"])

    def test_nvidia_unverified_provenance_fails(self):
        plan = {"lambda": 1.75, "momentum": 7, "lookback": 110}
        with self.assertRaises(ValueError):
            self.check(
                {"contract": "amos.ae.proposal-evidence.v1", "generator": "nvidia_nim",
                 "nim_status": "nim_invalid_response_schema",
                 "ai_provider_status": "nvidia_nim_validated_json",
                 "llm_hypothesis_generation_verified": True,
                 "candidate_parameters": [plan], "llm_generated_candidate_count": 1},
                {"contract": "amos.ae.autonomous-ledger.v1", "completed": []},
                {"contract": "amos.ae.autonomous-run.v1", "new_results": []})

    def test_no_fill_does_not_pass(self):
        plan = {"lambda": 1.25, "momentum": 6, "lookback": 90}
        result = self.check(
            {"contract": "amos.ae.proposal-evidence.v1", "generator": "openrouter_free",
             "ai_provider_status": "openrouter_free_validated_json", "llm_hypothesis_generation_verified": True,
             "candidate_parameters": [plan], "llm_generated_candidate_count": 1},
            {"contract": "amos.ae.autonomous-ledger.v1", "completed": []},
            {"contract": "amos.ae.autonomous-run.v1", "new_results": []})
        self.assertEqual(result["verdict"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
