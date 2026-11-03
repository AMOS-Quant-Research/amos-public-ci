"""Offline contract tests for the NIM fallback client."""
import importlib.util
import io
import os
import pathlib
import tempfile
import unittest
import urllib.error
from unittest import mock

spec = importlib.util.spec_from_file_location(
    "nim_client", pathlib.Path(__file__).resolve().parents[1] / "scripts" / "nim_client.py"
)
nim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nim)

def http_error(code):
    return urllib.error.HTTPError("https://example.invalid", code, "x", {}, io.BytesIO(b"{}"))

def ok():
    return {"choices": [{"message": {"content": "ok"}}]}

class NimClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ,
            {"NVIDIA_NIM_API_KEY": "key-a", "NIM_CLIENT_CACHE": str(pathlib.Path(self.tmp.name) / "cache.json")},
            clear=False,
        )
        self.env.start()
        for name in ("NIM_MODEL", "NIM_STRICT", "NIM_MODEL_CHAINS_FILE", "NIM_BASE_URL"):
            os.environ.pop(name, None)
        self.sleep = mock.patch.object(nim.time, "sleep", lambda _: None)
        self.sleep.start()

    def tearDown(self):
        self.sleep.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_same_scope_404_is_cached(self):
        first, second = nim.DEFAULT_CHAINS["fast"][:2]
        calls = []
        def post(_, __, payload, ___):
            calls.append(payload["model"])
            if len(calls) == 1:
                raise http_error(404)
            return ok()
        with mock.patch.object(nim, "_post", post):
            nim.chat("fast", [{"role": "user", "content": "x"}])
            nim.chat("fast", [{"role": "user", "content": "x"}])
        self.assertEqual(calls, [first, second, second])

    def test_cache_does_not_cross_endpoint_or_key(self):
        first = nim.DEFAULT_CHAINS["fast"][0]
        calls = []
        def unavailable(_, __, payload, ___):
            calls.append(payload["model"])
            raise http_error(404)
        with mock.patch.object(nim, "_post", unavailable):
            with self.assertRaises(nim.NimNoModelAvailable):
                nim.chat("fast", [{"role": "user", "content": "x"}], strict=True)
        with mock.patch.object(nim, "_post", lambda _, __, payload, ___: calls.append(payload["model"]) or ok()):
            os.environ["NIM_BASE_URL"] = "https://other.invalid/v1/chat/completions"
            nim.chat("fast", [{"role": "user", "content": "x"}], strict=True)
            os.environ.pop("NIM_BASE_URL")
            nim.chat("fast", [{"role": "user", "content": "x"}], key="key-b", strict=True)
        self.assertEqual(calls, [first, first, first])

    def test_model_parameter_is_rejected_before_request(self):
        with mock.patch.object(nim, "_post") as post:
            with self.assertRaisesRegex(ValueError, "do not pass model"):
                nim.chat("fast", [{"role": "user", "content": "x"}], model="other/model")
        post.assert_not_called()

    def test_selected_model_and_permitted_params_are_truthful(self):
        first = nim.DEFAULT_CHAINS["fast"][0]
        posted = {}
        def post(_, __, payload, ___):
            posted.update(payload)
            return ok()
        with mock.patch.object(nim, "_post", post):
            result = nim.chat("fast", [{"role": "user", "content": "x"}], temperature=0)
        self.assertEqual(posted["model"], first)
        self.assertEqual(result["model"], first)
        self.assertEqual(posted["temperature"], 0)

if __name__ == "__main__":
    unittest.main()
