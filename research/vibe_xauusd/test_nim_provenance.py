import json
import os
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ai_hypothesis_generator import CONTRACT, nim_propose, propose


class NIMProvenanceTests(unittest.TestCase):
    def test_mocked_model_response(self):
        class Response:
            def __enter__(self):
                body = {"choices": [{"message": {"content": json.dumps({
                    "candidates": [{"lambda": 1.75, "momentum": 7, "lookback": 110}]
                })}}]}
                return BytesIO(json.dumps(body).encode())
            def __exit__(self, *args):
                return False
        with patch.dict(os.environ, {"NVIDIA_NIM_API_KEY": "dummy_test_only",
                                     "NVIDIA_API_KEY": "", "NVIDIA_NIM_MODEL": "mock-model"}):
            with patch("ai_hypothesis_generator.urllib.request.urlopen", return_value=Response()):
                candidates, status = nim_propose([], [], 1)
        self.assertEqual(status, "nim_validated_json")
        self.assertEqual(candidates, [{"lambda": 1.75, "momentum": 7, "lookback": 110}])

    def test_fallback_cannot_claim_llm(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reg = root / "registry.json"
            reg.write_text(json.dumps({"contract": CONTRACT, "candidates": []}))
            with patch.dict(os.environ, {"NVIDIA_NIM_API_KEY": "", "NVIDIA_API_KEY": "",
                                         "NVIDIA_NIM_MODEL": ""}):
                report = propose(root / "missing-ledger.json", reg, root / "output.json", 2)
        self.assertFalse(report["llm_hypothesis_generation_verified"])
        self.assertEqual(report["llm_generated_candidate_count"], 0)
        self.assertEqual(report["heuristic_generated_candidate_count"], 2)


if __name__ == "__main__":
    unittest.main()
