# CODEX TASKS

任务基线见 V2.0 技术方案第 46-48 节。

当前状态：

- [x] C0-001 Monorepo 骨架
- [x] C0-002 基础设施目录（docker-compose 已存在）
- [x] C0-003 FastAPI 骨架（/health/live、/health/ready、request_id、structlog）
- [x] C0-004 SQLAlchemy/Alembic（P0 IAM/Entitlement/Workflow/Audit 初始迁移）
- [x] C0-005 Authentication（login/me/refresh/logout、Argon2id、JWT、refresh rotation/reuse detection）
- [x] C0-006 RBAC/ABAC/Entitlement 基座（权限目录、角色映射、ABAC 引擎、额度/特性检查）
- [x] C0-007 Workflow Event Store（task/task_version/workflow_event、SSE 读取模型、research/tasks API）
- [x] C0-008 Outbox Base（outbox_store、handler registry、dispatcher、receipt 幂等）
- [x] C0-009 Vue Skeleton（auth store、axios 拦截器、401 单飞刷新、登录页、主布局、路由守卫）
- [x] C0-010 OpenAPI -> TS（重新导出契约、生成 api-types、前端接入 workspace 类型）
- [x] C0-011 CI（Python lint/type/test、Web lint/format/typecheck/test、契约检查、安全扫描）

## P1 行情 / Technical / Market

- [x] C1-001 XTQuant Collector Skeleton（配置、日志、运行骨架、主入口）
- [ ] C1-002 SQLite/WAL
- [ ] C1-003 Ingest API
