#!/usr/bin/env bash
set -euo pipefail

export GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-owner/repo}"

docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --remove-orphans

for _ in $(seq 1 60); do
  if docker compose -f docker-compose.prod.yml ps backend --format '{{.Health}}' | grep -q healthy; then
    docker compose -f docker-compose.prod.yml ps
    exit 0
  fi
  sleep 3
done

echo "backend did not become healthy in time" >&2
docker compose -f docker-compose.prod.yml ps
exit 1
