# StudyBot: Production Plan

A free, local-first RAG chatbot for students. Upload PDF, PPTX, DOCX and YouTube links to a dashboard, then ask questions by text or voice. It starts with the PC, and the phone connects as an installable web app (PWA).

> **Status tracker** lives at the bottom. Every session ends with a write-up in [docs/sessions/](docs/sessions/).

"Flawless" is not achievable for a RAG system. What this plan gives you is **measurable quality gates** (section 9), so problems show up in evals rather than in front of students.

## 1. Baseline findings (legacy Proton project)

| Finding | Consequence |
|---|---|
| Legacy app is **Flask + Flask-SocketIO**, not FastAPI. It has no REST API. | StudyBot is a new FastAPI service. |
| Legacy app is a PC-control voice assistant with **no RAG and no LLM** (Ollama was removed in commit `f0880ce`). | Nothing to reuse for retrieval. |
| The intent classifier scores about 0.05 for **every** input (47 classes, near-uniform). "what is a binary search tree" routes to `GET_WEATHER`. Threshold is 0.05. | It cannot route "command vs. study question". Proton will call StudyBot by default and only run device commands on explicit patterns. |
| Wake word uses `recognize_google` in a loop. | Online, unofficial, unreliable. Replace with offline STT / openWakeWord. |
| OpenWeather key was hardcoded in git (`assistant.py`). | **Rotate the key** (history still contains it). Code now reads `OPENWEATHER_API_KEY`. |
| Agent tools include `run_command`, `run_code`, `write_file`. | StudyBot must have **no system tools**: uploaded documents are untrusted input. |
| Project lives in OneDrive. | Live data and the venv live in `%LOCALAPPDATA%\StudyBot`. |

**Hardware:** i5-10300H, 7.9 GB RAM, GTX 1650 (4 GB VRAM). Consequences: 3B-class LLM (Q4, about 2 GB VRAM), embeddings on CPU, no Docker, embedded databases only. The installed `llama3.1` 8B does not fit in 4 GB VRAM.

## 2. Assumptions

- For you and a small group, **served from your PC**. The phone is a client.
- If you mean many concurrent students, the hosting phase changes: a GTX 1650 serves about 1-2 concurrent chats.
- A phone cannot run the server at boot. The PC must be on unless an always-on fallback is added (section 7).

## 3. Architecture

```
Phone PWA ──┐                       ┌─ Ollama (LLM, localhost:11434)
Laptop web ─┼─ HTTPS (Tailscale) ─▶ FastAPI ─┼─ Chroma (vectors) + SQLite (metadata, FTS5/BM25)
Proton overlay ┘  REST + SSE + WS   │        └─ faster-whisper (STT) · Piper (TTS)
                                    └─ Worker process: extract → chunk → embed → index
```

Proton stays a **voice client** that calls `/api/chat`. Its PC-control skills stay separate.

## 4. Free stack

| Layer | Choice | Notes |
|---|---|---|
| API | FastAPI + Uvicorn, Pydantic v2, SQLite | Native SSE and WebSocket. |
| LLM | Ollama, `llama3.2:3b` or `qwen2.5:3b` (Q4) | Choose the winner on the golden set. `gemma2:2b` is the baseline. |
| Embeddings | `bge-small-en-v1.5` on CPU | Swap to `multilingual-e5-small` if content is not English. |
| Search | Chroma + SQLite FTS5, merged with RRF | Hybrid search catches exact terms. |
| Reranker | MiniLM cross-encoder, top 20 to top 5 | Keep only if the eval shows a gain. |
| PDF | PyMuPDF, `pypdf` fallback, OCR for scans | PyMuPDF is AGPL: fine for private use only. |
| PPTX / DOCX | `python-pptx` / `python-docx` | Slide = chunk unit; include speaker notes. |
| YouTube | `youtube-transcript-api`, then `yt-dlp` + faster-whisper | Store timestamps for `&t=` deep links. |
| STT | faster-whisper `base.en` / `small.en` (int8) | Replaces Google STT. |
| TTS | Piper offline, browser `speechSynthesis` on mobile, edge-tts optional | edge-tts is unofficial. |
| Wake word | openWakeWord (desktop overlay only) | Web app uses push-to-talk. |
| Frontend | React + Vite + Tailwind PWA | Installable on phone. |
| Remote access | Tailscale free tier (real HTTPS) | Phone browsers block the mic on plain `http://192.168.x.x`. |

**Free-forever core:** Ollama, faster-whisper, Piper, bge, Chroma, SQLite, FastAPI, React (all local). Google STT, edge-tts, the YouTube transcript API and cloud LLM free tiers are optional, because providers can change terms.

## 5. RAG design

- **Ingestion:** background jobs `pending → extracting → chunking → embedding → ready | failed`, progress over SSE. Dedupe by SHA-256; re-ingest replaces old chunks atomically.
- **Chunking:** structure-aware, about 500-800 tokens, 10-15% overlap, each chunk prefixed `Doc title › Heading`. PDFs by page/heading, PPTs by slide, YouTube by 60-90 s windows.
- **Organisation:** subject collections; retrieval filters on `user_id + collection_id`.
- **Query path:** rewrite follow-up → hybrid search (top 20-30) → optional rerank (top 5-6) → numbered-source prompt → streamed answer with `[n]` citations.
- **Guardrails:** low retrieval score → "That's not in your materials"; drop citations that don't map to a real chunk; document text is data, never instructions; "general knowledge" is a separate, labelled toggle (off by default).
- **API surface:**
  `POST /api/auth/login` · `GET|POST /api/collections` ·
  `POST /api/documents` · `POST /api/documents/youtube` · `GET|DELETE /api/documents/{id}` · `POST /api/documents/{id}/reindex` ·
  `GET /api/jobs/{id}/events` (SSE) · `POST /api/chat` (SSE) · `WS /api/voice` ·
  `GET /api/health` · `GET /api/ready`

## 6. Voice

Browser mic → WebSocket → VAD + faster-whisper → RAG → sentence-streamed TTS (first audio while tokens still generate). The user can interrupt (barge-in).

## 7. Startup and access

- **PC:** API and worker start via Task Scheduler (or NSSM) with restart-on-failure, installed by a `deploy/` script. The API waits for Ollama's `/api/tags`, then warms the LLM and embedding models. The server needs no interactive session because the mic lives in the browser/overlay.
- **Phone:** installs the PWA over Tailscale. If it must work with the PC off: an always-on spare machine, or a free cloud VM (Oracle Always Free ARM: slow for LLMs, availability hit-and-miss).

## 8. Production hardening

Local accounts with argon2 and HTTP-only cookies; per-user data isolation; uploads checked by magic bytes with size/page limits, UUID filenames and rate limits; locked-down CORS; no debug mode; structured logs; nightly SQLite + Chroma backup; pinned dependencies (`requirements.lock`); venv outside OneDrive.

## 9. Quality gates (proposed targets, to be measured on this hardware)

- Golden set of 60-100 questions from real student material, about 20% unanswerable.
- Retrieval hit@5 ≥ 85% (no LLM needed to measure).
- Faithfulness (answer supported by cited chunks) ≥ 90%: human spot-check + LLM judge.
- Correct refusal on ≥ 90% of unanswerable questions.
- Text time-to-first-token < 3 s; first voice audio < about 4 s.
- A pytest eval runs before any change to chunking, embeddings or prompts is accepted. UI thumbs up/down feeds new cases into the set.

## 10. Roadmap

| Phase | Time | Deliverable | Exit gate |
|---|---|---|---|
| **0. Cleanup** | 1-2 days | Rotate key, untrack personal data, remove junk, fix requirements, scaffold repo + venv, data outside OneDrive | Fresh install runs; tests pass |
| **1. Core RAG** | ~1 week | Loaders, chunker, indexer, hybrid retrieval, CLI, golden set + eval | hit@5 gate |
| **2. API + dashboard** | ~1 week | Job queue, auth, upload + YouTube UI, SSE progress | Upload → index → delete works end to end |
| **3. Chat + voice** | ~1 week | Streaming chat with citations, STT/TTS, PWA | Latency + refusal gates |
| **4. Deploy** | 3-4 days | Startup tasks, Tailscale HTTPS, backups, hardening | Reboot PC → ask a question from the phone |
| **5. Extras** | later | Proton as client, quizzes/flashcards, optional cloud LLM fallback | n/a |

## 11. Risks

| Risk | Mitigation |
|---|---|
| Only 8 GB RAM | One model loaded (`OLLAMA_MAX_LOADED_MODELS=1`), no Docker, embedded DBs |
| YouTube blocks / no captions | Whisper fallback |
| Scanned PDFs | OCR fallback |
| Small model hallucinates | Retrieval-score gate, citation validation, eval gate |
| PC off | Always-on fallback (section 7) |
| Prompt injection via documents | No tools in the chat path; documents treated as data |

## Status tracker

- [x] **Phase 0: Cleanup and foundations** (session 1, see [SESSION-01](docs/sessions/SESSION-01-phase0-foundations.md))
- [ ] Phase 1: Core RAG
- [ ] Phase 2: API + dashboard
- [ ] Phase 3: Chat + voice
- [ ] Phase 4: Deploy
- [ ] Phase 5: Extras
