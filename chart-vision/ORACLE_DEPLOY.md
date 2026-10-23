# Oracle Cloud deployment handoff (ARM64 or AMD64)
Status: **deployment-ready configuration only**. Not deployed, no OCI credentials, no model downloaded. Oracle Always Free compute availability, CPU/RAM limits and region quotas vary. Ollama image/model ARM64 compatibility must be checked on the chosen VM. Five independent upstream tools are not yet installed.
## On the Oracle VM (Ubuntu Linux with Docker Engine + Compose plugin)
1. Clone the existing repo, checkout `feat/chart-vision-mvp-32`, then `cd chart-vision`.
2. Set a strong secret in shell: `export AMOS_API_TOKEN="$(python3 -c 'import secrets;print(secrets.token_urlsafe(36))')"`. Save securely; do not commit.
3. `docker compose -f compose.oracle.yml up -d --build`
4. `docker compose -f compose.oracle.yml exec ollama ollama pull llava` (CPU inference may be too slow or fail due to memory).
5. `curl -fsS http://127.0.0.1:8765/healthz` (this checks HTTP readiness, **not model readiness**).
6. To test Ollama inference, send a genuine PNG/JPEG image to /analyze with `Authorization: Bearer <token>`; inspect the per-engine status. Other four return NOT_CONFIGURED until their validated adapter services are installed.
## iPhone access
The compose port is intentionally bound to VM loopback. Add authenticated HTTPS reverse proxy or a private tunnel (e.g. Tailscale), and open the HTTPS URL on iPhone. **Do not publicly expose port 8765 or Ollama 11434**. An iPhone physical-device acceptance test must be performed by the device owner.
## Acceptance
All five must report OK with distinct, verified real model outputs; consensus must report participating=5; cloud resource use and iPhone access must be measured. Mock CI PASS does not satisfy acceptance.
