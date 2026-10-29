import json
import os
import unittest
from unittest.mock import patch
from research.ai_trader.nim_candidate import validate,generate

class FakeResponse:
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,*args): return b'{"choices":[{"message":{"content":"{\\"period\\":21,\\"rsi_long\\":55,\\"rsi_short\\":45,\\"max_spread_atr\\":0.3}"}}]}'
class AdapterAndNimTests(unittest.TestCase):
    def test_no_nim_key_fails_closed(self):
        with patch.dict(os.environ,{"NVIDIA_NIM_API_KEY":""}):
            with self.assertRaisesRegex(RuntimeError,"NIM_SECRET_MISSING"):generate()
    def test_nim_provenance_from_actual_mocked_response(self):
        with patch.dict(os.environ,{"NVIDIA_NIM_API_KEY":"test"}):
            x=generate(request_fn=lambda req,timeout:FakeResponse())
        self.assertEqual(x["source"],"NVIDIA_NIM")
        self.assertEqual(x["parameters"]["period"],21)
        self.assertFalse(x["live_trading"])
    def test_bad_params_rejected(self):
        with self.assertRaises(ValueError):validate({"period":1})
