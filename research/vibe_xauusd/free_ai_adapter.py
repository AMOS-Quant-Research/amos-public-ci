"""Free-tier research-only LLM adapter; never submits orders."""
import json
import os
import urllib.request

def propose_free(prompt, count, valid, key, already):
    providers = (
        ("openrouter_free", "OPENROUTER_API_KEY", "OPENROUTER_FREE_MODEL",
         "meta-llama/llama-3.3-70b-instruct:free", "https://openrouter.ai/api/v1/chat/completions"),
        ("groq_free", "GROQ_API_KEY", "GROQ_FREE_MODEL",
         "llama-3.3-70b-versatile", "https://api.groq.com/openai/v1/chat/completions"),
    )
    statuses = []
    for provider, secret_name, model_name, default_model, endpoint in providers:
        token = os.getenv(secret_name, "")
        if not token:
            statuses.append(provider + "_not_configured")
            continue
        model = os.getenv(model_name) or default_model
        if provider == "openrouter_free" and not model.endswith(":free"):
            statuses.append(provider + "_nonfree_model_blocked")
            continue
        try:
            payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0.3, "max_tokens": 500}
            request = urllib.request.Request(endpoint, method="POST",
                data=json.dumps(payload).encode(),
                headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=30) as response:
                obj = json.load(response)
            content = obj["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            proposed = json.loads(content)["candidates"]
            if not isinstance(proposed, list):
                raise ValueError("not a list")
            seen = set(map(key, already))
            selected = []
            for item in proposed:
                if valid(item) and key(item) not in seen:
                    seen.add(key(item))
                    selected.append(item)
            if selected:
                return selected[:count], provider + "_validated_json"
            statuses.append(provider + "_invalid_candidates")
        except (OSError, ValueError, TypeError, KeyError, IndexError):
            statuses.append(provider + "_request_or_schema_failed")
    return None, ";".join(statuses)
