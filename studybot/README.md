# StudyBot

Free, local-first RAG chatbot for students. See [PLAN.md](PLAN.md) for the full plan and status.

## Quick start (Windows, PowerShell)

```powershell
cd studybot
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1   # venv in %LOCALAPPDATA%\StudyBot\venv
powershell -ExecutionPolicy Bypass -File scripts\test.ps1    # run tests
powershell -ExecutionPolicy Bypass -File scripts\run_dev.ps1 # API on http://127.0.0.1:8000
```

Check `/api/health` (liveness) and `/api/ready` (data dir, Ollama, LLM pulled). Docs at `/docs`.

## Try it from the command line (Phase 1)

Run from `studybot\backend` with the venv's Python (`%LOCALAPPDATA%\StudyBot\venv\Scripts\python.exe`).

```powershell
python -m app.cli ingest "C:\path\Unit_1_Notes.pdf" -c computer-vision   # PDF, PPTX, DOCX
python -m app.cli ingest "https://www.youtube.com/watch?v=VIDEO_ID" -c my-course
python -m app.cli list
python -m app.cli search "difference between sobel and laplacian" -c computer-vision   # no LLM
python -m app.cli ask "How does RANSAC reject outliers?" -c computer-vision            # cited answer
```

Collections are subjects: a question only searches the collections you name with `-c`
(omit it to search everything). Re-running `ingest` on an unchanged file is a no-op; on a changed
file it replaces the old version atomically.

Supported now: `.pdf` (text-based; scanned PDFs are detected but OCR is not built yet), `.pptx`,
`.docx`, and YouTube videos **that have English captions**. Old `.ppt` / `.doc` must be re-saved as
`.pptx` / `.docx`.

## Measuring quality

```powershell
python -m eval.run_retrieval --min-tokens 80 --rerank --show-misses   # hit@k, MRR, gate calibration
python -m eval.run_llm --models gemma2:2b                             # answers, refusals, latency
```

The 81-question golden set is `backend/eval/golden.jsonl`; the source list is `eval/corpus.json`.
Your own PDFs go in `%LOCALAPPDATA%\StudyBot\eval_corpus\` (they are never committed).

## Layout

```
studybot/
├── PLAN.md                 # plan + status tracker
├── backend/
│   ├── app/
│   │   ├── ingest/         # loaders (pdf, pptx, docx, youtube), chunker
│   │   ├── rag/            # embed, store (SQLite+FTS5+vectors), retrieve, rerank, prompt, pipeline
│   │   ├── core/ollama.py  # streaming chat client
│   │   ├── api/            # FastAPI routes (health so far)
│   │   ├── cli.py
│   │   └── config.py
│   ├── eval/               # golden set + retrieval and LLM evaluation scripts
│   ├── tests/
│   ├── requirements.txt    # runtime deps (ranges)
│   ├── requirements-dev.txt
│   └── requirements.lock   # exact versions used by setup.ps1
├── scripts/                # setup / run_dev / test
└── docs/sessions/          # one work-done write-up per session
```

## Where data lives

Runtime data (database, uploads, model files, transcript cache, logs, backups) and the virtualenv
live in `%LOCALAPPDATA%\StudyBot`, **not** in the repo. The repo is under OneDrive, and OneDrive
sync corrupts live SQLite files, so the app refuses to start with `STUDYBOT_HOME` inside OneDrive.
Override with `STUDYBOT_*` variables or `backend/.env` (see `.env.example`).
