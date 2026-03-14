## ACUBOT — Copilot / AI agent quick instructions

This file helps AI coding agents be productive quickly in this repository. Keep guidance short, actionable, and anchored to real files.

- Project type: Django app (simple project layout) with scraping utilities that produce JSON seed data.
- Primary app: `courses` (models in `courses/models.py`). Scrapers live in `scraper/` and write JSON to the repo root (`bologna_data.json`, `acibadem_data.json`).

Key developer flows (explicit examples)
- Run locally (fast): create a venv, install requirements, migrate, run server

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

- Run with Docker Compose (recommended for DB + LLM):

```bash
docker-compose up --build
# to run management commands while containers are up:
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python seed.py
```

Data flow and integration points (what to look for)
- Scrapers: `scraper/main_scraper.py` (requests + BeautifulSoup) and `scraper/bologna_scraper.py` (Selenium). They save data to `acibadem_data.json` / `bologna_data.json`.
- Seeding: `seed.py` reads `bologna_data.json` and creates `Faculty`, `Department`, and `Course` records (models in `courses/models.py`). Typical workflow: run scraper -> confirm JSON -> run seeder.
- DB: Postgres service configured in `docker-compose.yml` and database settings are in `config/settings.py` (note: credentials are hard-coded here; devs may prefer env vars).
- LLM: `docker-compose.yml` defines an `llm` service (Ollama at port 11434). There are currently no Python bindings in the repo that call it, but the container is available for local LLM experiments.

Project-specific conventions and gotchas
- Models: primary domain objects live in `courses/models.py`. `Course.code` is treated as unique.
- Scrapers write JSON to the repository root. `seed.py` expects `bologna_data.json` in the project root.
- `bologna_scraper.py` is Selenium-based and therefore requires `selenium` and a browser driver (not currently listed in `requirements.txt`). Running it in Docker as-is will likely fail unless the container is extended with browser binaries or you run it locally.
- Notable issues discovered (documented so agents don't assume a script runs):
  - `scraper/bologna_scraper.py` uses `if _name_ == "_main_":` (typo) so it won't execute when run directly. Also a minor string formatting/backslash in the final print. If you need to run it, change to `if __name__ == "__main__":` and ensure `selenium` + `webdriver-manager` are installed.
  - `requirements.txt` currently lists Django, psycopg2-binary, requests, beautifulsoup4; it does not include `selenium` or `webdriver-manager` used by the Selenium scraper.

Where to make changes / common edit locations
- Add/modify domain models: `courses/models.py` (create migrations via `python manage.py makemigrations` + `migrate`).
- Views / API: `courses/views.py` (currently minimal). Add serializers / endpoints as needed.
- Scrapers: `scraper/*.py` — prefer `main_scraper.py` for simple HTTP scraping (requests + bs4). Use Selenium only when necessary and document additional runtime requirements.

Testing & CI notes
- Tests are under `courses/tests.py` (currently minimal). Run tests with:

```bash
python manage.py test
```

Quick references (files)
- `manage.py` — Django CLI entrypoint
- `config/settings.py` — Django settings (DB credentials currently hard-coded)
- `docker-compose.yml` & `Dockerfile` — containerized dev environment (Postgres + Ollama + web)
- `scraper/` — scraping scripts that create JSON seed files
- `seed.py` — imports JSON into Django models

When editing, be conservative: follow existing patterns (simple models, direct DB seeding from JSON). If you introduce new long-running scrapers or headless browser use, update `requirements.txt` and document runtime steps in README.md and this file.

If you modify or add agent guidance here, ask the maintainer whether to include sensitive values (DB passwords) in settings or move them to env vars; current repo contains example credentials in `docker-compose.yml` and `config/settings.py`.

If anything above is unclear or you'd like more detail about any specific file or workflow, tell me which area to expand (e.g., run/debug Selenium scrapers, Dockerfile improvements, or adding CI tests) and I'll update this file.
