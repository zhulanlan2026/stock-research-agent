# PostgreSQL Backup / PITR Runbook

## 全量备份

```bash
docker exec research-postgres pg_dump -U research -Fc research_db \
  > backups/research_db_$(date +%F_%H%M%S).dump
```

## 恢复全量备份

```bash
docker exec -i research-postgres pg_restore -U research -d research_db \
  < backups/research_db_YYYY-MM-DD_HHMMSS.dump
```

## PITR

PostgreSQL 需要启用 `archive_mode` 和 `archive_command`，保留 WAL：

```text
archive_mode = on
archive_command = 'test ! -f /var/lib/postgresql/wal_archive/%f && cp %p /var/lib/postgresql/wal_archive/%f'
wal_level = replica
```

恢复时：

1. 停止业务写入。
2. 恢复最近全量备份。
3. 使用 recovery 配置回放到目标时间点。
4. 验证关键表和行数。

## 验证

- `SELECT count(*) FROM inbox_event;`
- `SELECT count(*) FROM market_bar;`
- `SELECT count(*) FROM financial_fact;`

## 自动化演练

`rc.yml` 会运行两个演练：

- `scripts/backup_restore_drill.sh`：全量逻辑备份（`pg_dump`）→ 恢复（`pg_restore`）→ 校验。
- `scripts/pitr_drill.sh`：物理备份（`pg_basebackup`）+ WAL 归档 + 按时间点恢复（`recovery_target_time`），并校验目标时间点之后的数据被正确丢弃。
