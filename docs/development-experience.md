# 开发经验与协作逻辑

这份文档用于沉淀本项目从 P0 到 P1 的实际开发经验，帮助你理解后续应该怎样拆任务、写代码、验证和提交。

## 1. 工作闭环

每次开发都按同一个闭环走：

```text
读基线
 -> 明确任务 ID
 -> 查现状
 -> 设计（必要时 ADR）
 -> 实现
 -> 测试
 -> 实盘 / 数据库核对
 -> 拆分提交
 -> 推送
```

不要一上来就写代码，先确认要做的任务在 V2.0 里的位置和边界。

## 已完成阶段与具体开发内容

### P0 基础骨架

- Monorepo 骨架。
- 基础设施目录与 docker-compose。
- FastAPI 骨架：`/health/live`、`/health/ready`、`request_id`、structlog。
- SQLAlchemy / Alembic 初始迁移。
- Authentication：登录、刷新、登出、Argon2id、JWT、刷新令牌轮换与复用检测。
- RBAC / ABAC / Entitlement 基座。
- Workflow Event Store：`task`、`task_version`、`workflow_event`、SSE 读取模型。
- Outbox Base：`outbox_store`、handler registry、dispatcher、receipt 幂等。
- Vue 骨架：auth store、axios 拦截器、401 单飞刷新、登录页、主布局、路由守卫。
- OpenAPI -> TS：导出契约、生成 api-types、前端接入 workspace 类型。
- CI：Python lint/type/test、Web lint/format/typecheck/test、契约检查、安全扫描。

### P1 行情 / Technical / Market

- XTQuant Collector Skeleton。
- 采集器本地 SQLite/WAL 持久化缓冲。
- Ingest API：`POST /api/v1/ingest/events`，事件幂等写入 `inbox_event`。
- WAL -> Ingest Transport：批量推送、成功标记 sent、失败保留 pending。
- XTQuant 行情采集适配：`subscribe_quote` 回调 -> 标准化 `QuoteEvent` -> WAL。
- Inbox -> Market Snapshot Consumer：消费 `inbox_event` 写入 `market_snapshot`。
- Market Snapshot Summary：`GET /market/snapshots/{symbol}/summary`。
- 前端行情展示、自动刷新、ECharts 价格走势图。
- 多标的监控：添加 / 移除标的、摘要卡片、选中切换。
- 历史 K 线聚合、行情异常状态提示、成交量副图。
- XTQuant 历史 K 线直落标准 `market_bar`。
- MA / EMA / MACD / RSI 指标计算与参数配置。
- 指标显示开关、参数模板、本地持久化、导入导出、主题切换。
- 多套命名配置方案管理、云端同步、冲突检测与处理。
- 冲突历史记录、导入 / 归档、自动清理策略。
- Redis Hot Snapshot：行情摘要热读缓存，PostgreSQL 仍为真相源。
- PostgreSQL Minute State：`market_minute_state` 一分钟粒度状态投影。
- Stock Identity Skill：股票代码 / 市场确定性规范化。
- Realtime Snapshot Skill：实时快照读取与 stale 标记。
- Technical Engine / Market Engine：确定性引擎边界。
- Reconnect / Gap Tests：WAL 失败重试、行情缺口检测。

当前 P1 已通过实盘链路验证，Windows collector 能持续把 `market.quote` / `market.bar` 推入 PostgreSQL，前端能显示真实行情、K 线和指标。

## 2. 先理解基线，再动手

唯一技术基线是：

`MiniQMT_智能研股系统_V2.0_最终技术方案_Codex开发执行版.md`

关键章节：

- 第 1 节：六条不可破坏原则
- 第 9 节：Schema 和迁移
- 第 46 节：P0-P6 实施路线
- 第 53 节：Single Source of Truth 规则

如果方案没有写清楚的执行细节，不要自行违背方案，而是补执行级设计 + ADR。

## 3. 一次只做一个小任务

推荐按任务 ID 工作：

```text
C0-001
C1-001
C2-001
...
```

一次完成一个小批次，避免一次改太多导致无法验证。

## 4. 开发规则

### 新增 Schema

必须同步：

- ORM 模型
- Pydantic DTO
- Alembic Migration
- 测试

示例：P1 新增 `market_minute_state` 时，同时补了模型、迁移、Store、consumer 调用和测试。

### 新增 API

必须同步：

- FastAPI 路由
- 认证 / 权限依赖
- 错误码
- `request_id`
- 测试
- OpenAPI 重新导出和前端类型

### 模型调用

正式模型调用必须走 Model Gateway，不允许业务代码直接调 DeepSeek。

### 正式副作用

必须走 Policy + Outbox，不允许 Agent 或普通业务代码直接执行外部副作用。

## 5. 实现步骤

1. 先查现状，避免重复造轮子。
2. 如果影响架构，先写 ADR。
3. 写模型 / 迁移 / Store / Service。
4. 写测试，优先覆盖关键规则和边界。
5. 跑局部测试，通过后再跑全量。
6. 跑 lint、typecheck、build。
7. 查真实数据库或接口，确认不是只在测试里通过。
8. 按功能拆分 commit。

## 6. 验证命令速查

### 后端测试

```bash
.venv/bin/python -m pytest apps/backend/tests apps/xtquant-collector/tests -q
```

### Lint / Typecheck

```bash
.venv/bin/ruff check .
.venv/bin/mypy .
```

### 前端

```bash
pnpm --filter @stock-research/web typecheck
pnpm --filter @stock-research/web lint
pnpm --filter @stock-research/web test
pnpm --filter @stock-research/web build
```

### 数据库迁移

```bash
cd apps/backend
../../.venv/bin/alembic -c alembic.ini upgrade head
```

### 查 PostgreSQL

```bash
docker exec research-postgres psql -U research -d research_db -c "SELECT ..."
```

## 7. 实盘核对经验

单元测试通过不等于真实链路正常。

P1 阶段我们实际查了：

- `inbox_event` 是否有待处理数据
- `market_snapshot` 是否持续增加
- `market_minute_state` 是否按分钟聚合
- `market_bar` 是否落库
- 前端默认周期是否和采集周期一致

结果发现前端默认 `1m`，但采集器当时只采 `1d`，导致 K 线和指标为空。所以实盘核对非常重要。

## 8. 提交拆分

不要把所有改动混在一个 commit。

按功能拆：

```text
feat(market): add PostgreSQL minute state projection
feat(market): add Redis hot snapshot cache
feat(market): add deterministic engines and skills
feat(market): add WAL retry and gap detection
docs: mark P1 complete in task list
```

每个 commit 都能独立理解、独立回滚。

## 9. 调试与权限

遇到 Docker 或数据库权限问题时，先用只读命令确认状态，再申请提升权限运行必要命令。

常用排障顺序：

```text
看状态
 -> 看日志
 -> 看表结构和行数
 -> 跑局部测试
 -> 跑全量测试
 -> 查真实 API 返回
```

## 10. 成长建议

想快速掌握这套开发方式，建议按顺序练：

1. 完整读一遍 V2.0 第 1 节和第 46 节。
2. 从 `C2-001 financial_fact` 开始，先只做一个小任务。
3. 亲手补 ORM + Migration + 测试，不要只改路由。
4. 每完成一个任务就查一次真实数据库。
5. 用拆分 commit 训练自己理解“最小可交付单元”。
6. 架构拿不准时，先写 ADR，再实施。
