"""Public CI NVIDIA NIM connectivity test. No credentials in repository."""
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_MODEL = "nvidia/nemotron-3.5-bolt-e4b"


def main():
    key = os.getenv("NVIDIA_NIM_API_KEY", "").strip()
    if not key:
        print("NIM_SECRET_MISSING")
        return 2
    model = os.getenv("NIM_MODEL", "").strip() or DEFAULT_MODEL
    payload = json.dumps({"model": model, "messages": [{"role": "user", "content": "Reply exactly AMOS_NIM_OK"}], "temperature": 0, "max_tokens": 32}).encode()
    req = urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions", data=payload, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            result = json.load(response)
        answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        if "AMOS_NIM_OK" not in answer:
            print("NIM_UNEXPECTED_RESPONSE", "model=" + model)
            return 3
        print("NIM_INFERENCE_OK", "model=" + model)
        return 0
    except urllib.error.HTTPError as exc:
        # A model can be listed in /v1/models and still be not callable for this account (404 "Not found for account").
        if exc.code == 404:
            print("NIM_MODEL_NOT_CALLABLE", "model=" + model, "HTTP 404: listed models may still be unavailable for this account; set NIM_MODEL to a callable model")
        elif exc.code == 410:
            print("NIM_MODEL_RETIRED", "model=" + model, "HTTP 410: model reached end of life; set NIM_MODEL to a current model")
        elif exc.code in (401, 403):
            print("NIM_AUTH_ERROR", "model=" + model, "HTTP", exc.code)
        else:
            print("NIM_HTTP_ERROR", "model=" + model, "HTTP", exc.code)
        return 4
    except Exception as exc:
        print("NIM_NETWORK_ERROR", type(exc).__name__)
        return 5

if __name__ == "__main__":
    sys.exit(main())
