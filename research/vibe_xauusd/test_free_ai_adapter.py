"""Offline regression tests for free AI provider routing; no credentials or network."""
import io
import json
import os
import unittest
from unittest.mock import patch
from free_ai_adapter import propose_free

def valid(p):
    return (isinstance(p, dict) and set(p) == {"lambda", "momentum", "lookback"}
            and type(p["lambda"]) in (float, int) and type(p["momentum"]) is int
            and type(p["lookback"]) is int and 0.1 <= p["lambda"] <= 5
            and 2 <= p["momentum"] <= 30 and 30 <= p["lookback"] <= 500)

def key(p):
    return p["lambda"], p["momentum"], p["lookback"]

class Response:
    def __init__(self, obj):
        self.data = io.BytesIO(json.dumps(obj).encode())
    def __enter__(self):
        return self.data
    def __exit__(self, *args):
        return False

class FreeAIAdapterTests(unittest.TestCase):
    def test_missing_keys_does_not_call_network(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "GROQ_API_KEY": ""}):
            with patch("free_ai_adapter.urllib.request.urlopen") as call:
                plans, status = propose_free("test", 2, valid, key, [])
        self.assertIsNone(plans)
        self.assertIn("not_configured", status)
        call.assert_not_called()

    def test_paid_openrouter_model_is_blocked(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "dummy",
                                     "OPENROUTER_FREE_MODEL": "paid-model",
                                     "GROQ_API_KEY": ""}):
            with patch("free_ai_adapter.urllib.request.urlopen") as call:
                plans, status = propose_free("test", 1, valid, key, [])
        self.assertIsNone(plans)
        self.assertIn("nonfree_model_blocked", status)
        call.assert_not_called()

    def test_mock_free_response_filters_invalid_and_duplicates(self):
        old = {"lambda": 1.0, "momentum": 5, "lookback": 80}
        fresh = {"lambda": 1.25, "momentum": 6, "lookback": 90}
        invalid = {"lambda": 99, "momentum": 6, "lookback": 90}
        body = {"choices": [{"message": {"content": json.dumps(
            {"candidates": [old, invalid, fresh]})}}]}
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "dummy",
                                     "OPENROUTER_FREE_MODEL": "mock:free",
                                     "GROQ_API_KEY": ""}):
            with patch("free_ai_adapter.urllib.request.urlopen", return_value=Response(body)):
                plans, status = propose_free("test", 3, valid, key, [old])
        self.assertEqual(plans, [fresh])
        self.assertEqual(status, "openrouter_free_validated_json")

    def test_network_error_falls_back_to_second_provider(self):
        fresh = {"lambda": 1.5, "momentum": 7, "lookback": 100}
        body = {"choices": [{"message": {"content": json.dumps({"candidates": [fresh]})}}]}
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "dummy",
                                     "OPENROUTER_FREE_MODEL": "mock:free",
                                     "GROQ_API_KEY": "dummy"}):
            with patch("free_ai_adapter.urllib.request.urlopen",
                       side_effect=[OSError("offline"), Response(body)]):
                plans, status = propose_free("test", 1, valid, key, [])
        self.assertEqual(plans, [fresh])
        self.assertEqual(status, "groq_free_validated_json")

if __name__ == "__main__":
    unittest.main()
