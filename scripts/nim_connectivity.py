"""Public CI NVIDIA NIM connectivity test. No credentials in repository."""
import json
import os
import sys
import urllib.error
import urllib.request

def main():
    key = os.getenv("NVIDIA_NIM_API_KEY", "").strip()
    if not key:
        print("NIM_SECRET_MISSING")
        return 2
    payload = json.dumps({"model": os.getenv("NIM_MODEL", "stepfun-ai/step-5-preview"), "messages": [{"role": "user", "content": "Reply exactly AMOS_NIM_OK"}], "temperature": 0, "max_tokens": 32}).encode()
    req = urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions", data=payload, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            result = json.load(response)
        answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        if "AMOS_NIM_OK" not in answer:
            print("NIM_UNEXPECTED_RESPONSE")
            return 3
        print("NIM_INFERENCE_OK")
        return 0
    except urllib.error.HTTPError as exc:
        print("NIM_HTTP_ERROR", exc.code)
        return 4
    except Exception as exc:
        print("NIM_NETWORK_ERROR", type(exc).__name__)
        return 5

if __name__ == "__main__":
    sys.exit(main())
