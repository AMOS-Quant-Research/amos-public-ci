"""Public CI NVIDIA NIM connectivity test. No credentials in repository.

Uses nim_client's "fast" chain. A model can be listed in /v1/models and still not be callable for this
account (404 "Not found for account"); the client then falls back and prints NIM_MODEL_FALLBACK.
Set NIM_STRICT=1 to forbid switching (the check then fails on the first unavailable model).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nim_client  # noqa: E402


def main():
    if not os.getenv("NVIDIA_NIM_API_KEY", "").strip():
        print("NIM_SECRET_MISSING")
        return 2
    try:
        result = nim_client.chat("fast", [{"role": "user", "content": "Reply exactly AMOS_NIM_OK"}],
                                 max_tokens=32, timeout=45, temperature=0)
    except nim_client.NimAuthError as exc:
        print("NIM_AUTH_ERROR", str(exc))
        return 4
    except nim_client.NimNoModelAvailable as exc:
        print("NIM_MODEL_NOT_CALLABLE", str(exc))
        return 4
    except nim_client.NimError as exc:
        print("NIM_HTTP_ERROR", str(exc))
        return 4
    except Exception as exc:
        print("NIM_NETWORK_ERROR", type(exc).__name__)
        return 5
    tag = "model=" + result["model"] + (" (fallback from " + result["requested_model"] + ")" if result["switched"] else "")
    if "AMOS_NIM_OK" not in result["content"]:
        print("NIM_UNEXPECTED_RESPONSE", tag)
        return 3
    print("NIM_INFERENCE_OK", tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
