# AMOS Chart Vision — Issue #32 MVP
Five parallel execution slots, iPhone-sized web UI, no paid API requirements, no order execution.
Run: `python chart-vision/app.py` then open localhost:8765.
Ollama requires locally running vision model. Other four tools require verified adapters and return NOT_CONFIGURED until connected.
This is NOT five independently functioning AIs yet. Do not expose the unauthenticated local server to the public Internet. HTTPS/authentication and cloud compute are separate deployment tasks.
