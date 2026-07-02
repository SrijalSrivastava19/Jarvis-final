# Jarvis — Phase 1: Voice Conversation System

A complete, working voice conversation loop: **wake word → speech-to-text → LLM reasoning with memory → text-to-speech**, served by a FastAPI backend and a Next.js UI.

## Architecture

```
┌─────────────┐      REST + WebSocket       ┌──────────────────────┐
│  Next.js UI │ ───────────────────────────▶ │   FastAPI Backend    │
│  (browser   │ ◀─────────────────────────── │                      │
│   mic/audio)│                              │  ┌────────────────┐  │
└─────────────┘                              │  │ routes_chat     │  │
                                              │  │ routes_voice    │  │
                                              │  │ routes_health   │  │
                                              │  └───────┬────────┘  │
                                              │          │           │
                                              │  ┌───────▼────────┐  │
                                              │  │   services/     │  │
                                              │  │  ollama_service │──┼──▶ Ollama (Llama 3.2)
                                              │  │  whisper_service│  │   local LLM
                                              │  │  piper_service  │──┼──▶ Piper binary (TTS)
                                              │  │  wakeword_service│ │
                                              │  │  memory_service │  │
                                              │  └───────┬────────┘  │
                                              │          │           │
                                              │  ┌───────▼────────┐  │
                                              │  │  SQLite (async) │  │
                                              │  │ conversations / │  │
                                              │  │    messages     │  │
                                              │  └─────────────────┘  │
                                              └──────────────────────┘
```

**Why these choices:**
- **faster-whisper** instead of `openai-whisper`: same model weights, 4x+ faster on CPU via CTranslate2 — important since this runs locally on a user's laptop, not a GPU server.
- **Piper as a subprocess**, not a Python binding: Piper is a standalone native binary; shelling out keeps it independently upgradable and avoids Python-version coupling.
- **SQLite via async SQLAlchemy** for Phase 1 memory: zero setup, but using the ORM (not raw SQL) means switching to Postgres later is a connection-string change, not a rewrite.
- **Wake word via Whisper + fuzzy match**: works fully offline today with zero extra dependencies. Documented limitation: this is heavier than a dedicated wake-word model. Phase 2+ should replace it with a lightweight always-on client-side detector (openWakeWord or Porcupine) that only calls the backend once triggered — the `wakeword_service.detect_*` interface is already shaped for that swap.
- **REST chaining in the UI's mic flow** (transcribe → chat → speak) rather than the WebSocket, for simplicity and easier debugging. The backend already exposes `/api/voice/ws` for a lower-latency streaming version — swapping the frontend to use it is a non-breaking Phase 2 change.

## Every file and what it does

```
backend/
  app/main.py                 FastAPI app: CORS, lifespan (DB init), router mounting, global error handlers
  app/config.py                Typed settings loaded from .env
  app/logger.py                Console + rotating file logging
  app/core/exceptions.py       Typed exception hierarchy -> consistent JSON error responses
  app/api/routes_health.py     GET /api/health — liveness + dependency reachability
  app/api/routes_chat.py       POST /api/chat, GET conversations — text chat with memory
  app/api/routes_voice.py      POST transcribe/speak/wake-word, WS /api/voice/ws — full voice loop
  app/services/ollama_service.py     Async Ollama client with retry/backoff
  app/services/whisper_service.py    faster-whisper STT, lazy-loaded singleton model
  app/services/piper_service.py      Piper TTS via subprocess
  app/services/wakeword_service.py   Wake-word fuzzy match on transcribed audio
  app/services/memory_service.py     Conversation/message persistence + context building
  app/models/schemas.py        Pydantic request/response contracts
  app/models/db_models.py      SQLAlchemy ORM: Conversation, Message
  app/db/database.py           Async engine/session, init_db()
  tests/                       pytest suite (chat + voice endpoints, wake word logic)
  requirements.txt, Dockerfile, .env.example

frontend/
  app/page.tsx                 Main screen: orb, mic button, chat panel, health badge
  app/layout.tsx, globals.css  Root layout + Tailwind globals
  components/VoiceOrb.tsx      Animated state indicator (idle/listening/thinking/speaking/error)
  components/MicButton.tsx     Records mic audio, drives transcribe -> chat -> speak pipeline
  components/ChatPanel.tsx     Scrollable message history + text input
  lib/api.ts                   Typed REST/WebSocket client for the backend
  package.json, tailwind.config.ts, next.config.js, tsconfig.json, Dockerfile

docker-compose.yml             Orchestrates ollama + backend + frontend
```

## Installation

### Prerequisites
- Python 3.11+
- Node.js 20+
- [Ollama](https://ollama.com) installed locally (or use the Docker Compose path below)
- [Piper](https://github.com/rhasspy/piper) binary on your PATH
- ffmpeg (required by Whisper for audio decoding)

### 1. Pull the LLM model
```bash
ollama pull llama3.2
```

### 2. Download a Piper voice
```bash
mkdir -p backend/voices && cd backend/voices
curl -L -o en_US-amy-medium.onnx \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx
curl -L -o en_US-amy-medium.onnx.json \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json
cd ../..
```

### 3. Backend setup
```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```
Visit `http://localhost:8000/docs` for interactive API docs.

### 4. Frontend setup
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```
Visit `http://localhost:3000`.

## Testing
```bash
cd backend
pytest -v
```
Tests cover: health check, chat creation/continuation with memory, error handling when Ollama is unreachable, transcription success/empty-audio rejection, speech synthesis, and wake-word matching logic. External services (Ollama, Piper, Whisper model loading) are mocked so tests run without those binaries installed.

## Deployment (Docker)
```bash
docker compose up --build
```
This starts Ollama, the backend, and the frontend together. After the containers are up, pull the model once into the Ollama container:
```bash
docker exec -it jarvis-ollama ollama pull llama3.2
```
Mount your downloaded Piper voice files into `backend/voices/` before starting — they're volume-mounted into the backend container.

For Render (per the original tech stack): deploy `backend` and `frontend` as separate Web Services using their respective Dockerfiles, and run Ollama on a Render Private Service or point `OLLAMA_BASE_URL` at a hosted Ollama instance, since Render's free tier doesn't reliably support the RAM/CPU Ollama needs for local inference.

## Known limitations (Phase 1 scope)
- Wake word detection re-transcribes audio with Whisper rather than using a dedicated lightweight detector — fine for testing, not yet optimized for always-on listening.
- Memory is exact conversational history only; no semantic/long-term memory yet (ChromaDB lands with the dedicated Memory feature phase).
- Single implicit user — no authentication yet (Firebase Auth is a later phase).
- No streaming token-by-token replies yet — Ollama responses are returned whole.

## What's next (Phase 2 candidates)
- Swap REST chaining in `MicButton.tsx` for the existing `/api/voice/ws` streaming endpoint to cut perceived latency.
- Client-side wake word (openWakeWord/Porcupine) for true always-on listening without hammering the backend.
- Streaming LLM responses (token-by-token) from Ollama through to the UI.
- Begin Feature 5+ (Daily News, Spotify, Gmail, Calendar) per the master plan, once you approve moving past Phase 1.
