"""NVIDIA NIM chat client with per-purpose model fallback.

Source of truth: AMOS-Quant-Research/amos-public-ci scripts/nim_client.py (NIM_CLIENT_VERSION below).
Other repositories keep an identical copy; change it here first, then copy.

Why: a model can be listed in /v1/models and still not be callable for this account
(HTTP 404 "Not found for account"), or be retired (HTTP 410). Instead of stopping, callers name a
purpose ("fast" / "heavy") and the client walks that purpose's priority list:

  404 / 410        -> model not callable: remember it (cache) and move to the next candidate
  429 / 5xx / net  -> transient: retry the same model with exponential backoff (max 3 retries),
                      then move to the next candidate
  read timeout     -> move to the next candidate without retrying (long generations)
  401 / 403        -> authentication problem: fail immediately, never switch

Research safety: a silent model change makes results incomparable. Every switch is printed to
stderr as NIM_MODEL_FALLBACK, the model actually used is returned (and should be written into the
artifact), and strict=True (or NIM_STRICT=1) forbids switching: only the first candidate is used.

Configuration without code changes:
  NIM_MODEL_CHAINS_FILE  JSON file {"fast": [...], "heavy": [...]} replacing DEFAULT_CHAINS per purpose
  NIM_MODEL              model to try first (prepended to the chain; with strict it is the only model)
  NIM_STRICT=1           forbid switching
  NIM_BASE_URL           chat/completions URL (default: integrate.api.nvidia.com)
  NIM_CLIENT_CACHE       status cache file (default: ~/.cache/amos-nim/model_status.json), TTL 1 hour
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

NIM_CLIENT_VERSION = "1.0.0"
DEFAULT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_CHAINS = {
    "fast": ["nvidia/nemotron-3.5-bolt-e4b", "nvidia/nemotron-3.5-lightning-30b-a3b",
             "nvidia/nemotron-3.5-super-vl-120b-a12b"],
    "heavy": ["nvidia/nemotron-3.5-super-vl-120b-a12b", "deepseek-ai/deepseek-v4.1-flash",
              "nvidia/nemotron-3.5-lightning-30b-a3b"],
}
CACHE_TTL_SECONDS = 3600
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1.0


class NimError(Exception):
    """Base error; .attempts lists what was tried."""

    def __init__(self, message, attempts=None):
        super().__init__(message)
        self.attempts = attempts or []


class NimAuthError(NimError):
    """401/403: the key is missing, invalid or not allowed. Switching models would not help."""


class NimNoModelAvailable(NimError):
    """Every candidate was unavailable (or strict mode forbade switching)."""


def model_chain(purpose, strict=None):
    chains = dict(DEFAULT_CHAINS)
    cfg = os.getenv("NIM_MODEL_CHAINS_FILE", "").strip()
    if cfg:
        chains.update(json.loads(Path(cfg).read_text(encoding="utf-8")))
    if purpose not in chains:
        raise ValueError(f"unknown purpose {purpose!r}; known: {sorted(chains)}")
    chain = list(chains[purpose])
    first = os.getenv("NIM_MODEL", "").strip()
    if first:
        chain = [first] + [m for m in chain if m != first]
    if is_strict(strict):
        chain = chain[:1]
    return chain


def is_strict(strict=None):
    if strict is not None:
        return bool(strict)
    return os.getenv("NIM_STRICT", "").strip().lower() in ("1", "true", "yes")


def _cache_path():
    p = os.getenv("NIM_CLIENT_CACHE", "").strip()
    return Path(p) if p else Path.home() / ".cache" / "amos-nim" / "model_status.json"


def _load_cache():
    try:
        data = json.loads(_cache_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    now = time.time()
    return {m: v for m, v in data.items() if now - v.get("checked", 0) < CACHE_TTL_SECONDS}


def _save_cache(cache):
    path = _cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(cache, indent=1), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass  # the cache is an optimisation only


def _post(url, key, payload, timeout):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST",
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def chat(purpose, messages, *, key=None, max_tokens=512, timeout=60, strict=None, **params):
    """Send one chat/completions request using the purpose's model chain.

    Returns {"content", "model", "requested_model", "switched", "attempts", "response"}.
    Raises NimAuthError (401/403, no switching) or NimNoModelAvailable.
    """
    key = (key if key is not None else os.getenv("NVIDIA_NIM_API_KEY", "")).strip()
    if not key:
        raise NimAuthError("NVIDIA_NIM_API_KEY is not set")
    url = os.getenv("NIM_BASE_URL", "").strip() or DEFAULT_URL
    chain = model_chain(purpose, strict)
    strict_mode = is_strict(strict)
    cache = _load_cache()
    attempts = []
    for model in chain:
        known = cache.get(model)
        if known and known.get("status") == "unavailable" and not strict_mode:
            attempts.append({"model": model, "result": f"skipped (cached HTTP {known.get('code')})"})
            continue
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens, **params}
        for retry in range(MAX_RETRIES + 1):
            try:
                data = _post(url, key, payload, timeout)
            except urllib.error.HTTPError as exc:
                code = exc.code
                if code in (401, 403):
                    attempts.append({"model": model, "result": f"HTTP {code}"})
                    raise NimAuthError(f"NIM authentication failed (HTTP {code}); not switching models", attempts)
                if code in (404, 410):
                    attempts.append({"model": model, "result": f"HTTP {code}"})
                    cache[model] = {"status": "unavailable", "code": code, "checked": time.time()}
                    _save_cache(cache)
                    break
                if code == 429 or code >= 500:
                    attempts.append({"model": model, "result": f"HTTP {code} (retry {retry})"})
                    if retry < MAX_RETRIES:
                        time.sleep(BACKOFF_BASE_SECONDS * (2 ** retry))
                        continue
                    break
                attempts.append({"model": model, "result": f"HTTP {code}"})
                raise NimError(f"NIM request failed for {model} (HTTP {code})", attempts)
            except TimeoutError:
                # A timed-out long generation is not retried on the same model (would multiply the wait).
                attempts.append({"model": model, "result": f"timeout after {timeout}s"})
                break
            except (urllib.error.URLError, ConnectionError) as exc:
                attempts.append({"model": model, "result": f"network error {type(exc).__name__} (retry {retry})"})
                if retry < MAX_RETRIES:
                    time.sleep(BACKOFF_BASE_SECONDS * (2 ** retry))
                    continue
                break
            else:
                cache[model] = {"status": "ok", "checked": time.time()}
                _save_cache(cache)
                attempts.append({"model": model, "result": "ok"})
                switched = model != chain[0]
                if switched:
                    print(f"NIM_MODEL_FALLBACK purpose={purpose} requested={chain[0]} used={model} "
                          f"attempts={json.dumps(attempts)}", file=sys.stderr)
                message = (data.get("choices") or [{}])[0].get("message", {})
                return {"content": message.get("content") or "", "model": model, "requested_model": chain[0],
                        "switched": switched, "attempts": attempts, "response": data}
        if strict_mode:
            break
    why = "strict mode: switching forbidden" if strict_mode else "no candidate was callable"
    raise NimNoModelAvailable(f"NIM: {why} for purpose={purpose} (tried {[a['model'] for a in attempts]})", attempts)
