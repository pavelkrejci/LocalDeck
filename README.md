# LocalDeck

LocalDeck is an MVP that discovers web services bound to localhost, fingerprints them and exposes a small dashboard.

This repository contains a minimal Phase 1 implementation: async port scanning, HTTP/HTTPS detection, title and favicon extraction, SQLite persistence, simple naming engine, a minimal dashboard (Jinja2 + FastAPI) and a small CLI.

Quick start (local):

1. Create a virtualenv with Python 3.12+
2. Install dependencies: poetry install (or pip install -r requirements)
3. Run locally: localdeck serve

Quick start (docker):

1. docker-compose up --build
2. Open http://127.0.0.1:7575

See docs in README for configuration, security notes and further development plan.
