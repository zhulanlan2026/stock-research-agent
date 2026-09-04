#!/usr/bin/env bash
set -euo pipefail

PG_USER="${POSTGRES_USER:-research}"
PG_PASSWORD="${POSTGRES_PASSWORD:-research123}"
PG_DB="${POSTGRES_DB:-research_db}"
PG_IMAGE="${POSTGRES_IMAGE:-postgres:15-alpine}"

DRILL_DIR="$(mktemp -d)"
WAL_DIR="$DRILL_DIR/wal_archive"
BASE_DIR="$DRILL_DIR/basebackup"
mkdir -p "$WAL_DIR" "$BASE_DIR"
chmod 777 "$WAL_DIR" "$BASE_DIR"

cleanup() {
  docker rm -f pitr-pg pitr-recover >/dev/null 2>&1 || true
  docker run --rm -v "$DRILL_DIR:/drill:rw" --entrypoint rm "$PG_IMAGE" -rf /drill >/dev/null 2>&1 || true
}
trap cleanup EXIT

# 1. Start PostgreSQL with WAL archiving enabled.
docker run -d --name pitr-pg \
  -e POSTGRES_USER="$PG_USER" -e POSTGRES_PASSWORD="$PG_PASSWORD" -e POSTGRES_DB="$PG_DB" \
  -v "$WAL_DIR:/wal_archive" \
  -v "$BASE_DIR:/basebackup" \
  "$PG_IMAGE" \
  -c wal_level=replica \
  -c archive_mode=on \
  -c 'archive_command=test ! -f /wal_archive/%f && cp %p /wal_archive/%f' \
  -c archive_timeout=5

# 2. Wait until PostgreSQL accepts connections.
for _ in $(seq 1 60); do
  if docker exec pitr-pg pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker exec pitr-pg pg_isready -U "$PG_USER" -d "$PG_DB"

# 3. Create a table and take a physical base backup.
docker exec pitr-pg psql -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 -c \
  "CREATE TABLE pitr_test (id serial PRIMARY KEY, val text, created_at timestamptz DEFAULT now());"
docker exec pitr-pg pg_basebackup -U "$PG_USER" -D /basebackup -X stream

# 4. Write a row that must survive PITR.
docker exec pitr-pg psql -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 -c \
  "INSERT INTO pitr_test (val) VALUES ('before-pitr');"
sleep 3

# 5. Recovery target time, between the two writes.
RECOVERY_TIME="$(docker exec pitr-pg psql -U "$PG_USER" -d "$PG_DB" -Atc \
  "SELECT to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS');")"
echo "recovery target (UTC): $RECOVERY_TIME"
sleep 3

# 6. Write a row that must be dropped by PITR.
docker exec pitr-pg psql -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 -c \
  "INSERT INTO pitr_test (val) VALUES ('after-pitr');"
# Force a WAL segment switch so the 'after-pitr' WAL is archived before disaster.
docker exec pitr-pg psql -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 -c "SELECT pg_switch_wal();"
sleep 2

# 7. Simulate disaster: destroy the primary (its data directory dies with it).
docker rm -f pitr-pg

# 8. Prepare recovery: base backup becomes PGDATA, recovery.signal triggers replay.
touch "$BASE_DIR/recovery.signal"
chmod 644 "$BASE_DIR/recovery.signal"

docker run -d --name pitr-recover \
  -e POSTGRES_USER="$PG_USER" -e POSTGRES_PASSWORD="$PG_PASSWORD" -e POSTGRES_DB="$PG_DB" \
  -v "$BASE_DIR:/var/lib/postgresql/data" \
  -v "$WAL_DIR:/wal_archive" \
  "$PG_IMAGE" \
  -c 'restore_command=cp /wal_archive/%f %p' \
  -c "recovery_target_time=$RECOVERY_TIME"

# 9. Wait for recovery to finish and the recovered instance to accept connections.
for _ in $(seq 1 90); do
  if ! docker ps --format '{{.Names}}' | grep -q '^pitr-recover$'; then
    echo "recover container exited unexpectedly, logs:" >&2
    docker logs pitr-recover >&2 || true
    exit 1
  fi
  if docker exec pitr-recover psql -U "$PG_USER" -d "$PG_DB" -Atc "SELECT 1;" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

# 10. Verify: only the pre-PITR row should remain.
RESTORED="$(docker exec pitr-recover psql -U "$PG_USER" -d "$PG_DB" -Atc \
  "SELECT string_agg(val, ',' ORDER BY id) FROM pitr_test;")"
echo "restored rows: $RESTORED"

if [ "$RESTORED" != "before-pitr" ]; then
  echo "PITR verification failed: expected 'before-pitr', got '$RESTORED'" >&2
  exit 1
fi

echo "PITR drill OK: recovered to $RECOVERY_TIME, 'after-pitr' correctly absent"
