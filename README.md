# AgentForge Workspace (Starter)

A polished, responsive AI-agent workspace built with Flask + HTML/CSS/JavaScript. The UI borrows broad modern SaaS dashboard patterns; it is not affiliated with Claude or Anthropic.

## Features
- Dashboard overview, agent list, Engine, Build, Studio, Deployments, API Keys, LLM Gateway, Updates & Runtime.
- Create agents with name, description, Fast/Pro/Max tier, long-form instructions, intended tools, connection notes, skills, workspace memory, channels and schedule notes.
- Run an agent through an OpenAI-compatible `/chat/completions` provider using its instructions and memory.
- Runtime inspector shows Python version and installed package names/versions.
- Small dependency footprint; agent/settings data stored as JSON locally.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:8000`.

To use a model, open **API Keys** and **LLM Gateway**, enter a valid provider key/base URL/model IDs, then create an agent and use **Studio**. Alternatively set `LLM_API_KEY` and `LLM_BASE_URL` in the environment. Fast/Pro/Max are UI tiers, not universal model names; choose model IDs your provider account actually supports.

## GitHub and deployment

1. Create a GitHub repository and upload these files.
2. For a live Python backend, deploy the repository as a Python web service on a Python-capable host. The included `Procfile` runs `gunicorn app:app`; set the service's start command to `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120` if needed.
3. Add `LLM_API_KEY` and optionally `LLM_BASE_URL` as host environment secrets. Do not commit API keys.
4. Open `/health` to verify the backend responds.

**Important:** GitHub Pages serves static files and does not execute this Flask backend. A GitHub upload by itself does not make a Python server live. GitHub Actions can run jobs but is not a continuously running web server. Free host plans and persistence rules can change; verify the chosen host's current terms.

## Limitations and production notes
- JSON storage is intended for a single-user demo. Some hosting filesystems are ephemeral and may reset on redeploy/restart; use a persistent disk or database if saved agents must survive.
- This starter does not implement user authentication, multi-user isolation, OAuth connections, web search, code execution, file tools, real scheduling, or autonomous self-updates. Tool/connection/channel/schedule entries are configuration notes until you connect real implementations.
- API key entered in the UI is saved in `data/settings.json` for this simple starter. For a public production deployment, use environment secrets and implement authentication/authorization before enabling credential management. Keep `data/` private and never commit it.
- Runtime inspection is read-only. It intentionally does not modify its own source code, run arbitrary package installation, or automatically commit changes to GitHub. Self-updating code safely requires version control, tests, review, rollback, and restricted credentials.
- Add authentication, CSRF protection, rate limiting, request quotas, robust logging, database migrations, and stricter secret management before exposing this app publicly.

## Optional single-Python-file variant

`agentforge_single.py` embeds the HTML/CSS/JavaScript UI directly in the Python file. It still requires the packages in `requirements.txt`, and it still needs a Python-capable host to run the backend. For maintainability, the default multi-file version is recommended.
