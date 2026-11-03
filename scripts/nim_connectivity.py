"""Public-safe NIM connectivity probe using the same shared client as research."""
import os
import sys

from scripts import nim_client

def main():
    if not os.getenv("NVIDIA_NIM_API_KEY", "").strip():
        print("NIM_SECRET_MISSING")
        return 2
    try:
        result = nim_client.chat(
            "fast",
            [{"role": "user", "content": "Reply exactly AMOS_NIM_OK"}],
            max_tokens=32,
            timeout=45,
            temperature=0,
        )
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
    tag = "model=" + result["model"]
    if result["switched"]:
        tag += " (fallback from " + result["requested_model"] + ")"
    if "AMOS_NIM_OK" not in result["content"]:
        print("NIM_UNEXPECTED_RESPONSE", tag)
        return 3
    print("NIM_INFERENCE_OK", tag)
    return 0

if __name__ == "__main__":
    sys.exit(main())
