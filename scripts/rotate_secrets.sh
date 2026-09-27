#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
COLLECTOR_ENV="$PROJECT_DIR/apps/akshare-collector/.env"

PYTHON_BIN="$(command -v python3 || command -v python)"

JWT_SECRET="$("$PYTHON_BIN" -c 'import secrets; print(secrets.token_urlsafe(48))')"
INGEST_TOKEN="$("$PYTHON_BIN" -c 'import secrets; print(secrets.token_urlsafe(48))')"

set_env_value() {
    local file="$1"
    local key="$2"
    local value="$3"
    if grep -q "^${key}=" "$file" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$file"
    else
        printf '%s=%s\n' "$key" "$value" >> "$file"
    fi
}

set_env_value "$ENV_FILE" "JWT_SECRET_KEY" "$JWT_SECRET"
set_env_value "$ENV_FILE" "COLLECTOR_INGEST_TOKEN" "$INGEST_TOKEN"
set_env_value "$COLLECTOR_ENV" "COLLECTOR_INGEST_TOKEN" "$INGEST_TOKEN"

echo "secrets rotated in .env and apps/akshare-collector/.env"
echo "remember to restart backend and the collector for the new values to take effect"
