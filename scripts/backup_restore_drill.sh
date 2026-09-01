#!/usr/bin/env bash
set -euo pipefail

DB_USER="${POSTGRES_USER:-research}"
DB_NAME="${POSTGRES_DB:-research_db}"
DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"
export PGPASSWORD="${POSTGRES_PASSWORD:-research123}"

PSQL="psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -v ON_ERROR_STOP=1 -q"
DUMP="/tmp/research_db.dump"

# Deterministic baseline: only drill rows live in inbox_event.
$PSQL -c "TRUNCATE inbox_event;"
$PSQL -c "INSERT INTO inbox_event (id, event_id, event_type, payload, received_at)
          VALUES (gen_random_uuid(), 'drill-1', 'market.snapshot', '{\"symbol\":\"600519.SH\"}'::jsonb, now()),
                 (gen_random_uuid(), 'drill-2', 'market.snapshot', '{\"symbol\":\"000001.SZ\"}'::jsonb, now());"

before=$($PSQL -Atc "SELECT count(*) FROM inbox_event;")
echo "baseline inbox_event rows: $before"

pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -Fc "$DB_NAME" > "$DUMP"
echo "backup size: $(du -h "$DUMP" | cut -f1)"

$PSQL -c "TRUNCATE inbox_event;"
after_delete=$($PSQL -Atc "SELECT count(*) FROM inbox_event;")
if [ "$after_delete" != "0" ]; then
  echo "expected 0 rows after truncate, got $after_delete" >&2
  exit 1
fi

pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  --data-only --table=inbox_event "$DUMP"

restored=$($PSQL -Atc "SELECT count(*) FROM inbox_event;")
if [ "$restored" != "$before" ]; then
  echo "restore mismatch: before=$before restored=$restored" >&2
  exit 1
fi

echo "backup/restore drill OK: $restored inbox_event rows restored"
