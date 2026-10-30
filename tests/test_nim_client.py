"""Offline contract tests for scripts/nim_client.py (no network: urlopen is replaced)."""
import importlib.util
import io
import json
import os
import pathlib
import tempfile
import unittest
import urllib.error
from unittest import mock

spec = importlib.util.spec_from_file_location(
    "nim_client", pathlib.Path(__file__).resolve().parents[1] / "scripts" / "nim_client.py")
nim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nim)


def http_error(code):
    return urllib.error.HTTPError("https://example.invalid", code, "x", {}, io.BytesIO(b"{}"))


def ok(content="AMOS_NIM_OK"):
    return {"choices": [{"message": {"content": content}}]}


class NimClientTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"NVIDIA_NIM_API_KEY": "test-key", "NIM_CLIENT_CACHE":
                                                os.path.join(self.tmp.name, "cache.json")}, clear=False)
        self.env.start()
        for k in ("NIM_MODEL", "NIM_STRICT", "NIM_MODEL_CHAINS_FILE"):
            os.environ.pop(k, None)
        mock.patch.object(nim.time, "sleep", lambda s: None).start()

    def tearDown(self):
        mock.patch.stopall()
        self.env.stop()
        self.tmp.cleanup()

    def run_chat(self, responses, **kw):
        calls = []

        def fake_post(url, key, payload, timeout):
            calls.append(payload["model"])
            r = responses.get(payload["model"], ok())
            r = r.pop(0) if isinstance(r, list) else r
            if isinstance(r, Exception):
                raise r
            return r

        with mock.patch.object(nim, "_post", fake_post):
            return nim.chat("fast", [{"role": "user", "content": "x"}], **kw), calls

    def test_404_falls_back_and_reports_model(self):
        first, second = nim.DEFAULT_CHAINS["fast"][:2]
        res, calls = self.run_chat({first: http_error(404)})
        self.assertEqual(res["model"], second)
        self.assertTrue(res["switched"])
        self.assertEqual(calls, [first, second])

    def test_cache_skips_known_unavailable_model(self):
        first = nim.DEFAULT_CHAINS["fast"][0]
        self.run_chat({first: http_error(410)})
        res, calls = self.run_chat({})
        self.assertNotIn(first, calls)
        self.assertTrue(res["switched"])

    def test_401_fails_without_switching(self):
        first = nim.DEFAULT_CHAINS["fast"][0]
        with self.assertRaises(nim.NimAuthError):
            self.run_chat({first: http_error(401)})

    def test_transient_errors_retry_same_model(self):
        first = nim.DEFAULT_CHAINS["fast"][0]
        res, calls = self.run_chat({first: [http_error(503), http_error(429), ok()]})
        self.assertEqual(res["model"], first)
        self.assertFalse(res["switched"])
        self.assertEqual(calls, [first, first, first])

    def test_timeout_moves_on_without_retry(self):
        first, second = nim.DEFAULT_CHAINS["fast"][:2]
        res, calls = self.run_chat({first: TimeoutError()})
        self.assertEqual(calls, [first, second])
        self.assertEqual(res["model"], second)

    def test_strict_forbids_switching(self):
        first = nim.DEFAULT_CHAINS["fast"][0]
        with self.assertRaises(nim.NimNoModelAvailable):
            self.run_chat({first: http_error(404)}, strict=True)

    def test_chain_file_overrides_defaults(self):
        cfg = os.path.join(self.tmp.name, "chains.json")
        pathlib.Path(cfg).write_text(json.dumps({"fast": ["vendor/model-a", "vendor/model-b"]}), encoding="utf-8")
        os.environ["NIM_MODEL_CHAINS_FILE"] = cfg
        self.assertEqual(nim.model_chain("fast"), ["vendor/model-a", "vendor/model-b"])


if __name__ == "__main__":
    unittest.main()
