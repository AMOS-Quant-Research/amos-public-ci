import os
import unittest
from unittest.mock import patch

from research.ai_trader.nim_candidate import generate, validate

def valid_result(**overrides):
    result = {
        "content": '{"period":21,"rsi_long":55,"rsi_short":45,"max_spread_atr":0.3}',
        "model": "nvidia/nemotron-3.5-bolt-e4b",
        "requested_model": "nvidia/nemotron-3.5-bolt-e4b",
        "switched": False,
        "response": {"choices": [{"message": {"content": "candidate"}}]},
    }
    result.update(overrides)
    return result

class AdapterAndNimTests(unittest.TestCase):
    def test_no_nim_key_fails_closed(self):
        with patch.dict(os.environ, {"NVIDIA_NIM_API_KEY": ""}):
            with self.assertRaisesRegex(RuntimeError, "NIM_SECRET_MISSING"):
                generate()

    def test_nim_provenance_uses_actual_called_model(self):
        with patch.dict(os.environ, {"NVIDIA_NIM_API_KEY": "test"}):
            item = generate(chat_fn=lambda *args, **kwargs: valid_result(
                model="nvidia/nemotron-3.5-lightning-30b-a3b",
                requested_model="nvidia/nemotron-3.5-bolt-e4b",
                switched=True,
            ))
        self.assertEqual(item["source"], "NVIDIA_NIM")
        self.assertEqual(item["parameters"]["period"], 21)
        self.assertEqual(item["model"], "nvidia/nemotron-3.5-lightning-30b-a3b")
        self.assertTrue(item["model_fallback"])
        self.assertFalse(item["live_trading"])

    def test_invalid_nim_json_is_rejected_before_native_run(self):
        with patch.dict(os.environ, {"NVIDIA_NIM_API_KEY": "test"}):
            with self.assertRaises(ValueError):
                generate(chat_fn=lambda *args, **kwargs: valid_result(content='{"period":1}'))

    def test_bad_params_rejected(self):
        with self.assertRaises(ValueError):
            validate({"period": 1})
