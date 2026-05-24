#!/bin/bash
set -e

echo "Deploying Video-Generate..."

# Set environment
ENV=${1:-production}
COMPOSE_FILE="docker-compose.yml"

if [ "$ENV" = "gpu" ]; then
    COMPOSE_FILE="docker-compose.gpu.yml"
fi

# Pull latest images
docker compose -f "$COMPOSE_FILE" pull

# Deploy
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

# Cleanup old images
docker image prune -f

echo "Deployment complete! ($ENV mode)"
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"
