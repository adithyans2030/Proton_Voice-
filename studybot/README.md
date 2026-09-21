# StudyBot

Free, local-first RAG chatbot for students. See [PLAN.md](PLAN.md) for the full plan and status.

## Quick start (Windows, PowerShell)

```powershell
cd studybot
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1   # venv in %LOCALAPPDATA%\StudyBot\venv
powershell -ExecutionPolicy Bypass -File scripts\test.ps1    # run tests
powershell -ExecutionPolicy Bypass -File scripts\run_dev.ps1 # API on http://127.0.0.1:8000
```

Then open <http://127.0.0.1:8000/docs>, or check `/api/health` (liveness) and `/api/ready` (data dir, Ollama, LLM pulled).

Pull the default model once: `ollama pull llama3.2:3b`.

## Layout

```
studybot/
├── PLAN.md                 # plan + status tracker
├── backend/
│   ├── app/                # FastAPI app (config, api, core)
│   ├── tests/
│   ├── requirements.txt    # runtime deps (ranges)
│   ├── requirements-dev.txt
│   └── requirements.lock   # exact versions used by setup.ps1
├── scripts/                # setup / run_dev / test
└── docs/sessions/          # one work-done write-up per session
```

## Where data lives

Runtime data (databases, uploads, index, logs, backups) and the virtualenv live in `%LOCALAPPDATA%\StudyBot`, **not** in the repo. The repo is under OneDrive, and OneDrive sync corrupts live SQLite/vector files, so the app refuses to start with `STUDYBOT_HOME` inside OneDrive. Override with `STUDYBOT_*` variables or `backend/.env` (see `.env.example`).
