#!/usr/bin/env bash
set -euo pipefail

export GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-owner/repo}"
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
