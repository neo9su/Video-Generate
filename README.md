# Video-Generate

AI-powered video generation & remake platform. Generates product videos from text prompts, swaps faces, removes watermarks, and clones voices using LLMs + ComfyUI + CosyVoice.

## Features

- **Video Generation** — Text-to-video with scenes, narration, subtitles
- **Face Swap Remake** — Upload video + face image for AI face replacement
- **Voice Cloning** — Clone voice from audio sample for re-narration
- **Watermark Removal** — Mark fixed/moving watermark areas; auto-removed via FFmpeg/LaMa
- **Video Preview & Download** — Completed tasks show inline video player + download button
- **Face Enhancement** — GFPGAN/CodeFormer improves facial details
- **GPU Pipeline** — FaceFusion (CUDA) for face swap on 2x RTX 3090

## Architecture

| Layer | Stack |
|-------|-------|
| Frontend | Next.js 14 + React + Tailwind CSS |
| Backend | FastAPI + Celery workers |
| Database | PostgreSQL 16 |
| Cache/Broker | Redis 7 |
| Objects | MinIO |
| Reverse Proxy | Nginx (:8082 → frontend:3000 + backend:8000) |
| Monitor | Grafana + Prometheus |

### GPU Server (10.190.0.222)

- 2x RTX 3090 (24GB each) · CUDA 12.8
- FaceFusion for face swap · ComfyUI for T2I generation
- SSH: `neo@10.190.0.222` (password: enet,2000)

## Quick Start

```bash
cp .env.example .env
docker compose -f docker-compose.gpu.yml up -d
```

Access: http://localhost:8082 (via nginx) or http://localhost:3000 (frontend)

## Services

| Service | Port | Description |
|---------|------|-------------|
| Nginx | 8082 | Reverse proxy (unified entry) |
| Frontend | 3000 | Next.js web UI |
| Backend API | 8000 | FastAPI REST API |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache / Celery broker |
| MinIO | 9000-9001 | Object storage |

## Key API Endpoints

### Remake (Face Swap)
- `POST /api/v1/remake/remake` — Submit remake task
- `GET /api/v1/remake/remake/{id}` — Get task status
- `GET /api/v1/remake/remake/{id}/download` — Download video

### Watermark
- `POST /api/v1/watermark/frames` — Extract first/last frames
- `POST /api/v1/watermark/segments` — Scene change detection
- `POST /api/v1/watermark/segment-frames` — Extract per-segment frames

## Project Structure

```
backend/       - FastAPI app (services, routers, workers)
frontend/      - Next.js 14 app
nginx/         - nginx config (reverse proxy)
scripts/       - Setup & deployment
docker-compose*.yml — Docker Compose configs
```

## Tech Stack

- **LLM API**: DeepSeek v4 / Qwen2.5 / Gemini 2.5
- **Image Gen**: ComfyUI (dreamshaper_8 / SD models)
- **Video Gen**: Sulphur 2 / Wan2.2 via ComfyUI
- **Face Swap**: FaceFusion 3.6.1 (inswapper_128)
- **TTS**: Edge TTS + CosyVoice 2
- **Voice Clone**: CosyVoice 2 (zero-shot)

## License

MIT
