# Video-Generate

AI-powered video generation platform. Generates videos from text prompts using LLM script generation, ComfyUI for image/video creation, and CosyVoice for TTS narration.

## Architecture

- **Backend**: FastAPI + Celery workers + PostgreSQL + Redis
- **Frontend**: Next.js 14 + React + Tailwind CSS
- **External Services**: LLM API, ComfyUI, CosyVoice

## Quick Start

1. Copy the environment file:
   ```bash
   cp .env.example .env
   ```

2. Start with Docker Compose:
   ```bash
   docker compose up -d
   ```

3. Access the app:
   - Frontend: http://localhost:3000
   - API: http://localhost:8000/docs

## Project Structure

```
backend/       - FastAPI backend
frontend/      - Next.js frontend
scripts/       - Setup and deployment scripts
docker-compose.yml     - Standard deployment
docker-compose.gpu.yml - GPU-enabled deployment
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Next.js web UI |
| Backend API | 8000 | FastAPI REST API |
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Message broker & cache |

## License

MIT
