"""NVIDIA NIM chat client with scoped, per-purpose model fallback.

The client returns the model actually called and isolates unavailable-model cache
entries by endpoint and API credential context. It never emits or persists a key.
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_CHAINS = {
    "fast": [
        "nvidia/nemotron-3.5-bolt-e4b",
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        "nvidia/nemotron-3.5-super-vl-120b-a12b",
    ],
    "heavy": [
        "nvidia/nemotron-3.5-bolt-e4b",
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        "nvidia/nemotron-3.5-super-vl-120b-a12b",
    ],
}
CACHE_TTL_SECONDS = 3600
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1.0

class NimError(Exception):
    def __init__(self, message, attempts=None):
        super().__init__(message)
        self.attempts = attempts or []

class NimAuthError(NimError):
    pass

class NimNoModelAvailable(NimError):
    pass

def is_strict(strict=None):
    if strict is not None:
        return bool(strict)
    return os.getenv("NIM_STRICT", "").strip().lower() in ("1", "true", "yes")

def model_chain(purpose, strict=None):
    chains = dict(DEFAULT_CHAINS)
    path = os.getenv("NIM_MODEL_CHAINS_FILE", "").strip()
    if path:
        chains.update(json.loads(Path(path).read_text(encoding="utf-8")))
    if purpose not in chains:
        raise ValueError(f"unknown purpose {purpose!r}; known: {sorted(chains)}")
    chain = list(chains[purpose])
    preferred = os.getenv("NIM_MODEL", "").strip()
    if preferred:
        chain = [preferred] + [candidate for candidate in chain if candidate != preferred]
    return chain[:1] if is_strict(strict) else chain

def _cache_path():
    value = os.getenv("NIM_CLIENT_CACHE", "").strip()
    return Path(value) if value else Path.home() / ".cache" / "amos-nim" / "model_status.json"

def _cache_scope(url, key):
    """Opaque namespace; neither URL nor credential is written to disk."""
    return hashlib.sha256(f"{url}\0{key}".encode("utf-8")).hexdigest()

def _load_cache():
    try:
        data = json.loads(_cache_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    now = time.time()
    scoped = {}
    for scope, entries in data.items():
        if not isinstance(entries, dict):
            continue  # ignore unsafe legacy model-only records
        valid = {
            model: entry for model, entry in entries.items()
            if isinstance(entry, dict) and now - entry.get("checked", 0) < CACHE_TTL_SECONDS
        }
        if valid:
            scoped[scope] = valid
    return scoped

def _save_cache(cache):
    path = _cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(cache, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(temporary, path)
    except OSError:
        pass

def _post(url, key, payload, timeout):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)

def chat(purpose, messages, *, key=None, max_tokens=512, timeout=60, strict=None, **params):
    """Call one purpose chain and report exactly the model posted to NIM."""
    if "model" in params:
        raise ValueError("model is selected by purpose/NIM_MODEL; do not pass model to chat()")
    key = (key if key is not None else os.getenv("NVIDIA_NIM_API_KEY", "")).strip()
    if not key:
        raise NimAuthError("NVIDIA_NIM_API_KEY is not set")
    url = os.getenv("NIM_BASE_URL", "").strip() or DEFAULT_URL
    chain = model_chain(purpose, strict)
    strict_mode = is_strict(strict)
    cache = _load_cache()
    scope = _cache_scope(url, key)
    scoped_cache = cache.setdefault(scope, {})
    attempts = []
    for model in chain:
        known = scoped_cache.get(model)
        if known and known.get("status") == "unavailable" and not strict_mode:
            attempts.append({"model": model, "result": f"skipped (cached HTTP {known.get('code')})"})
            continue
        payload = {**params, "model": model, "messages": messages, "max_tokens": max_tokens}
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
                    scoped_cache[model] = {"status": "unavailable", "code": code, "checked": time.time()}
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
                attempts.append({"model": model, "result": f"timeout after {timeout}s"})
                break
            except (urllib.error.URLError, ConnectionError) as exc:
                attempts.append({"model": model, "result": f"network error {type(exc).__name__} (retry {retry})"})
                if retry < MAX_RETRIES:
                    time.sleep(BACKOFF_BASE_SECONDS * (2 ** retry))
                    continue
                break
            else:
                attempts.append({"model": model, "result": "ok"})
                switched = model != chain[0]
                if switched:
                    print(
                        f"NIM_MODEL_FALLBACK purpose={purpose} requested={chain[0]} used={model} attempts={json.dumps(attempts)}",
                        file=sys.stderr,
                    )
                message = (data.get("choices") or [{}])[0].get("message", {})
                return {
                    "content": message.get("content") or "",
                    "model": model,
                    "requested_model": chain[0],
                    "switched": switched,
                    "attempts": attempts,
                    "response": data,
                }
        if strict_mode:
            break
    why = "strict mode: switching forbidden" if strict_mode else "no candidate was callable"
    raise NimNoModelAvailable(f"NIM: {why} for purpose={purpose}", attempts)
