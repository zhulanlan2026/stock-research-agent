#!/usr/bin/env bash
set -euo pipefail

uv run python scripts/export_openapi.py
pnpm --filter @stock-research/api-types generate
git diff --exit-code -- packages/shared-contracts/openapi/openapi.json packages/api-types/src
