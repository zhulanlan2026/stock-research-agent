# 国金 MiniQMT 智能研股系统
## V2.0 最终技术方案 / Codex 开发执行版

> **文档性质：Single Source of Truth（唯一技术基线）**  
> 本文合并并取代此前：
> - V1.0《Codex 技术开发执行方案》
> - V1.2《Codex 工程规范最终版》
>
> 自 V2.0 起，Codex、开发人员、测试、运维和架构评审只以本文件为准。旧版本仅归档，不再作为实施依据。

---

# 0. 文档定位

## 0.1 项目目标

建设一个生产级、可审计、可复现、可授权、可追溯的 **个股智能研究平台**。

系统不是“股票聊天网页”，也不是“LLM 自动写研报”，而是由：

- Web
- API
- MiniQMT/XTQuant 数据采集
- 确定性 Engine
- Evidence / Claim / Snapshot
- Hybrid Retrieval
- LangGraph Multi-Agent
- Skill Gateway
- Policy Engine
- HITL
- Outbox
- 可观测性
- 灰度与恢复

共同组成的完整研究平台。

## 0.2 首期产品形态

首期：

- 浏览器 Web
- Vue 3 + Vite + TypeScript
- FastAPI 后端
- Windows MiniQMT/XTQuant Collector
- DeepSeek 官方 API
- LangGraph
- PostgreSQL / Redis / MinIO / Milvus / Neo4j

## 0.3 明确不做

首期不建设：

- 全市场自动选股
- Alpha 策略
- 收益率预测交易信号
- 自动策略回测
- 组合优化
- 自动下单
- 自动交易执行
- LLM 猜测匿名客户
- LLM 猜测隐藏供应链
- LLM 猜测未公开订单
- LLM 推断未确认收入并作为正式事实
- Agent 直接执行正式外部副作用

---

# 1. 六条不可破坏的架构原则

## 1.1 前后端严格分离

Vue 3 仅调用：

```text
/api/v1/**
```

前端禁止：

- 直连 PostgreSQL
- 直连 Redis
- 直连 MinIO
- 直连 Milvus
- 直连 Neo4j
- 直连 MiniQMT/XTQuant
- 直连 DeepSeek
- 直接调用内部 Skill

所有业务能力统一通过 FastAPI。

---

## 1.2 PostgreSQL 是业务与状态唯一真相源

PostgreSQL 保存：

- IAM
- Permission
- Entitlement
- Workflow
- Research Snapshot
- Risk
- Decision
- Report
- Audit
- Outbox
- Human Review
- Structured Data

以下均不是业务真相源：

- Redis
- Milvus
- Neo4j
- Celery Result Backend
- 浏览器本地状态

原则：

> Redis 清空、Milvus 重建、Neo4j 重建后，正式业务状态仍可恢复。

---

## 1.3 正式数字和正式状态由确定性 Engine 产生

正式：

- 财务指标
- 技术指标
- 评分
- Risk Level
- Opportunity Snapshot
- Decision Snapshot
- 订单生命周期状态

必须由：

- 代码
- 公式
- 规则
- 统计
- 已版本化数据

确定性生成。

LLM 负责：

- 理解
- 抽取
- 查询改写
- 解释
- 报告生成
- 语义审核
- 情景描述

LLM 不得成为正式数字真相源。

---

## 1.4 数据先授权，再检索

任何：

- Document
- Chunk
- Evidence
- Claim
- Graph Edge
- Snapshot

在进入 Retrieval 或 Agent 前必须完成：

- tenant
- user
- visibility
- owner
- license
- purpose
- symbol
- as_of

权限约束。

---

## 1.5 Skill 默认拒绝

Agent 不能因为“注册了工具”就调用。

Skill Gateway 每次执行前必须检查：

```text
authentication
-> scope
-> role
-> entitlement
-> agent whitelist
-> task binding
-> data scope
-> model egress policy
-> risk/system state
-> budget
-> side-effect permission
```

默认结果：

```text
DENY
```

只有显式满足规则才执行。

---

## 1.6 正式副作用统一走 Policy + Outbox

以下动作不能由 Agent 直接执行：

- 正式报告发布
- 通知发送
- 图谱正式发布
- 正式 Claim 发布
- 高风险导出
- 管理员高危变更

统一：

```text
Agent / Service
    ↓
Policy Engine
    ↓
ALLOW / REVIEW / DENY
    ↓
Outbox
    ↓
Worker
    ↓
Side Effect Receipt
```

---

# 2. 总体系统架构

```text
Browser
  |
  v
Nginx / TLS / CORS / CSRF / Rate Limit
  |
  +----------------------------+
  |                            |
  v                            v
Vue 3 Web                    FastAPI
                              /api/v1
                                |
              +-----------------+--------------------+
              |                 |                    |
              v                 v                    v
            IAM             Entitlement            Policy
              |                 |                    |
              +-----------------+--------------------+
                                |
                                v
                      Research / File / Review API
                                |
                                v
                         PostgreSQL Truth
                                |
         +----------------------+-----------------------+
         |                      |                       |
         v                      v                       v
       Redis                  MinIO                   Celery
                                                        |
                    +-------------------------+----------+---------+
                    |                         |                    |
                    v                         v                    v
             research-worker           document-worker    notification-worker
                    |                         |
                    v                         v
                LangGraph              Parser / Evidence
                    |                         |
                    +------------+------------+
                                 |
                                 v
                           Skill Gateway
                                 |
              +------------------+------------------+
              |                  |                  |
              v                  v                  v
            Engine           Retrieval          Connectors
              |                  |                  |
      PostgreSQL/Redis     Milvus/Neo4j       DeepSeek / Data Sources

Windows:
MiniQMT / XTQuant
      ↓
xtquant_collector
      ↓
SQLite/WAL
      ↓
Outbound TLS
      ↓
Backend Ingest API
```

---

# 3. 最终 Monorepo 结构

```text
stock-research-platform/
│
├─ apps/
│  ├─ web/
│  │  ├─ public/
│  │  ├─ src/
│  │  │  ├─ main.ts
│  │  │  ├─ App.vue
│  │  │  ├─ app/
│  │  │  ├─ api/
│  │  │  │  ├─ client.ts
│  │  │  │  ├─ interceptors/
│  │  │  │  └─ generated/
│  │  │  ├─ router/
│  │  │  │  └─ guards/
│  │  │  ├─ layouts/
│  │  │  ├─ features/
│  │  │  ├─ components/
│  │  │  ├─ composables/
│  │  │  ├─ stores/
│  │  │  ├─ charts/
│  │  │  ├─ contracts/
│  │  │  ├─ constants/
│  │  │  ├─ directives/
│  │  │  ├─ styles/
│  │  │  ├─ assets/
│  │  │  └─ utils/
│  │  ├─ tests/
│  │  │  ├─ unit/
│  │  │  ├─ component/
│  │  │  └─ fixtures/
│  │  ├─ e2e/
│  │  ├─ package.json
│  │  ├─ vite.config.ts
│  │  ├─ tsconfig.json
│  │  └─ .env.example
│  │
│  ├─ backend/
│  │  ├─ src/
│  │  │  └─ stock_research/
│  │  │     ├─ __init__.py
│  │  │     ├─ py.typed
│  │  │     ├─ main.py
│  │  │     ├─ api/
│  │  │     │  └─ v1/
│  │  │     ├─ core/
│  │  │     ├─ auth/
│  │  │     ├─ iam/
│  │  │     ├─ entitlements/
│  │  │     ├─ agents/
│  │  │     ├─ graphs/
│  │  │     ├─ skills/
│  │  │     ├─ engines/
│  │  │     │  ├─ fundamental/
│  │  │     │  ├─ technical/
│  │  │     │  ├─ market/
│  │  │     │  ├─ risk/
│  │  │     │  ├─ scenario/
│  │  │     │  └─ decision/
│  │  │     ├─ retrieval/
│  │  │     ├─ documents/
│  │  │     ├─ connectors/
│  │  │     ├─ stores/
│  │  │     ├─ policies/
│  │  │     ├─ schemas/
│  │  │     ├─ workers/
│  │  │     ├─ outbox/
│  │  │     └─ observability/
│  │  ├─ tests/
│  │  │  ├─ unit/
│  │  │  └─ api/
│  │  ├─ migrations/
│  │  │  ├─ env.py
│  │  │  ├─ script.py.mako
│  │  │  └─ versions/
│  │  ├─ alembic.ini
│  │  ├─ pyproject.toml
│  │  ├─ Dockerfile
│  │  └─ .env.example
│  │
│  └─ xtquant-collector/
│     ├─ src/
│     │  └─ xtquant_collector/
│     │     ├─ __init__.py
│     │     ├─ py.typed
│     │     ├─ main.py
│     │     ├─ config/
│     │     ├─ xtquant/
│     │     ├─ wal/
│     │     ├─ transport/
│     │     └─ observability/
│     ├─ tests/
│     │  └─ unit/
│     ├─ pyproject.toml
│     ├─ README.md
│     └─ .env.example
│
├─ packages/
│  ├─ api-types/
│  │  ├─ src/
│  │  ├─ package.json
│  │  └─ README.md
│  └─ shared-contracts/
│     ├─ errors/
│     │  └─ error-codes.json
│     ├─ enums/
│     │  ├─ research-mode.json
│     │  ├─ risk-level.json
│     │  └─ evidence-level.json
│     ├─ schemas/
│     │  └─ sse-events.schema.json
│     ├─ feature-flags/
│     │  └─ feature-flags.json
│     └─ README.md
│
├─ infrastructure/
│  ├─ docker/
│  ├─ nginx/
│  ├─ postgres/
│  ├─ redis/
│  ├─ minio/
│  ├─ milvus/
│  ├─ neo4j/
│  └─ monitoring/
│     ├─ prometheus/
│     └─ grafana/
│
├─ tests/
│  ├─ integration/
│  ├─ e2e/
│  ├─ retrieval/
│  ├─ risk_replay/
│  ├─ security/
│  └─ performance/
│
├─ docs/
│  ├─ architecture/
│  ├─ adr/
│  ├─ api/
│  └─ runbooks/
│
├─ scripts/
│  ├─ export_openapi.py
│  ├─ generate_api_types.sh
│  └─ check_contracts.sh
│
├─ .github/
│  ├─ workflows/
│  │  ├─ ci.yml
│  │  ├─ security.yml
│  │  └─ contract-check.yml
│  └─ CODEOWNERS
│
├─ AGENTS.md
├─ ARCHITECTURE.md
├─ CODEX_TASKS.md
├─ pyproject.toml
├─ uv.lock
├─ pnpm-workspace.yaml
├─ pnpm-lock.yaml
├─ docker-compose.yml
├─ Makefile
├─ .editorconfig
├─ .pre-commit-config.yaml
├─ .gitignore
├─ .env.example
└─ README.md
```

---

# 4. 技术栈锁定

## 4.1 Web

- Vue 3
- Composition API
- Vite
- TypeScript
- Vue Router
- Pinia
- Element Plus
- ECharts
- Axios
- Zod
- Vitest
- Vue Test Utils
- Playwright
- ESLint
- Prettier
- Stylelint

## 4.2 Backend

- Python 3.10 x64
- uv
- FastAPI
- Uvicorn
- Pydantic v2
- pydantic-settings
- SQLAlchemy 2
- Alembic
- asyncpg
- httpx
- tenacity
- orjson
- Celery
- Redis
- Flower
- structlog
- OpenTelemetry
- Prometheus
- argon2-cffi
- PyJWT
- cryptography

## 4.3 Agent / LLM

- LangGraph
- langchain-core
- OpenAI-compatible client
- jsonschema
- DeepSeek 官方 API

## 4.4 Data

- pandas
- polars
- numpy
- scipy
- statsmodels
- pandera
- duckdb

## 4.5 Documents

- MinerU
- PyMuPDF
- pdfplumber
- python-docx
- openpyxl
- lxml

---

# 5. Python / pnpm Workspace

## 5.1 uv Workspace

根：

```toml
[tool.uv.workspace]
members = [
    "apps/backend",
    "apps/xtquant-collector",
]

[tool.ruff]
target-version = "py310"

[tool.mypy]
python_version = "3.10"
strict = true

[tool.pytest.ini_options]
addopts = "-ra"
```

统一：

```bash
uv sync
uv run ruff check .
uv run mypy .
uv run pytest
```

## 5.2 pnpm Workspace

```yaml
packages:
  - "apps/web"
  - "packages/*"
```

命名：

```text
@stock-research/web
@stock-research/api-types
```

---

# 6. API 契约唯一来源

## 6.1 REST API

唯一关系：

```text
FastAPI / Pydantic
      ↓
    OpenAPI
      ↓
packages/api-types
      ↓
Vue API layer
```

`packages/api-types`：

- 自动生成
- 禁止手改
- CI 校验

## 6.2 shared-contracts

仅保存稳定的跨语言协议：

- Error Code
- Risk Level
- Evidence Level
- Research Mode
- SSE Event Schema
- Feature Flag Key

不以 `shared-contracts -> Pydantic` 作为 REST DTO 主流程。

---

# 7. Makefile / Contract CI

```makefile
openapi:
	uv run python scripts/export_openapi.py

api-types: openapi
	pnpm --filter @stock-research/api-types generate

contracts-check:
	uv run python scripts/export_openapi.py
	pnpm --filter @stock-research/api-types generate
	git diff --exit-code
```

CI：

```text
Pydantic changed
  ↓
Export OpenAPI
  ↓
Generate TS
  ↓
git diff --exit-code
```

不一致即失败。

---

# 8. 配置规范

`.env.example`：

```dotenv
APP_ENV=development
APP_NAME=stock-research-platform
API_V1_PREFIX=/api/v1

DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...

MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=

MILVUS_URI=http://localhost:19530

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=
NEO4J_PASSWORD=

DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=
MODEL_FAST=
MODEL_RESEARCH=
MODEL_REVIEW=
MODEL_FALLBACK=
MODEL_DISCOVERY_ON_STARTUP=true
EXTERNAL_MODEL_DEFAULT_DENY=true

JWT_ISSUER=stock-research
JWT_AUDIENCE=stock-research-web
ACCESS_TOKEN_TTL_MINUTES=15
REFRESH_TOKEN_TTL_DAYS=14

SSE_HEARTBEAT_SECONDS=15
MAX_UPLOAD_MB=100

OTEL_SERVICE_NAME=stock-research-backend
```

生产：

- Secret Manager
- 环境隔离
- Key 隔离
- DB 隔离
- Object Bucket 隔离

---

# 9. Backend Schema 与迁移

## P0 IAM / Entitlement / Workflow / Audit

### iam

- tenant
- user
- identity
- credential
- session
- device
- role
- permission
- user_role
- mfa_factor

### entitlement

- plan
- subscription
- entitlement_event
- quota_ledger
- analysis_symbol_quota

### workflow

- task
- task_version
- workflow_event
- checkpoint_ref
- inbox_event
- outbox_event
- side_effect_receipt

### audit

- audit_event
- policy_decision
- model_usage
- data_access_log

## P1 market

- quote_snapshot
- bar_1m
- bar_daily
- market_context

## P2 fundamental / research

- financial_fact
- feature_snapshot
- peer_snapshot
- quality_snapshot
- valuation_snapshot
- research_snapshot
- opportunity_snapshot
- risk_snapshot
- decision_snapshot
- report
- report_version

## P3 evidence

- source
- document
- document_version
- evidence
- claim
- risk_claim
- authorization_policy

## P4 supply_chain

- contract
- order
- order_status_event
- organization_alias
- graph_publish_event

## P5 review

- human_review
- human_review_event
- review_assignment

---

# 10. 数据索引与分区

- 多租户高频索引第一列含 `tenant_id`
- 时序：`symbol + as_of/trade_date`
- `bar_1m` 按月或季度分区
- 热数据 PostgreSQL
- 历史归档 Parquet
- `document` 唯一：
  `source_id + external_id + revision_no`
- Evidence 去重：
  `root_evidence_id + content_hash`
- `workflow_event` 唯一：
  `task_id + sequence_no`
- `outbox_event.effect_key` 唯一
- Audit 月分区

---

# 11. 核心领域对象

## VerifiedDataObject

```json
{
  "symbol": "000001.SZ",
  "metric": "revenue",
  "period": "2026Q2",
  "value": 1000000000,
  "unit": "CNY",
  "source_id": "source_xxx",
  "disclosed_at": "2026-08-01T09:00:00+08:00",
  "available_at": "2026-08-01T09:05:00+08:00",
  "revision_no": 1,
  "truth_status": "VERIFIED"
}
```

## Evidence

```json
{
  "evidence_id": "ev_xxx",
  "root_evidence_id": "rev_xxx",
  "doc_id": "doc_xxx",
  "page": 12,
  "section": "主要合同",
  "content_hash": "sha256:...",
  "source_level": "E1",
  "authorization": {
    "visibility_scope": "PUBLIC",
    "license_policy_id": null
  },
  "citation_ready": true
}
```

## Claim

```json
{
  "subject": "公司A",
  "predicate": "signed_contract_with",
  "object": "客户B",
  "valid_from": "2026-07-01",
  "valid_to": null,
  "evidence_ids": ["ev_xxx"],
  "verification_status": "DRAFT",
  "confidence": 0.88
}
```

## Snapshot

```json
{
  "snapshot_id": "snap_xxx",
  "symbol": "000001.SZ",
  "as_of": "2026-08-21T14:30:00+08:00",
  "module_version": "technical:1.0.0",
  "data_versions": {},
  "coverage": 0.92,
  "freshness": {},
  "evidence_ids": []
}
```

---

# 12. Data Trust / Evidence Level

| Level | Source | Usage |
|---|---|---|
| E1 | 交易所、正式财报、监管、正式公告 | 事实根证据 |
| E2 | 已验收结构化接口、官方统计 | 指标和行情事实 |
| E3 | 授权研报、行业报告、公开招投标 | 观点、假设、风险线索 |
| E4 | 主流财经/行业媒体 | 事件线索，需要回溯 |
| E5 | 论坛/传闻 | 仅线索队列 |
| AI-X | AI 原文抽取 | 候选，绑定页码和原文 |
| AI-G | AI 总结/推断 | 解释/情景，不是事实 |

规则：

- 原始文件先写 MinIO
- 生成 `content_hash`
- 禁止仅保存抽取结果
- 多源冲突不覆盖
- 冲突生成 `CONFLICTED`
- 关键事实保留 PIT `available_at`
- Research Agent 仅使用 `citation_ready=true` 形成事实性结论

---

# 13. MiniQMT / XTQuant Collector

## 13.1 进程边界

Collector：

- Windows 原生
- 独立 Python App
- 独立 service principal
- 只主动出站
- 不对公网开放 MiniQMT

## 13.2 流程

```text
XTQuant Callback / Pull
    ↓
Normalize
    ↓
SQLite WAL
    ↓
batch_id
    ↓
Outbound TLS
    ↓
Backend Ingest
    ↓
PostgreSQL
    ↓
ACK
    ↓
WAL Cleanup
```

## 13.3 必须实现

- WAL
- idempotent batch
- reconnect
- gap detection
- retry
- disk threshold alert
- heartbeat
- stale monitoring
- signed/authenticated ingest

---

# 14. 文档处理

## 14.1 Parser Router

| Type | Parser |
|---|---|
| PDF | MinerU |
| PDF fallback/校验 | PyMuPDF / pdfplumber |
| DOCX | python-docx |
| XLSX | openpyxl |
| HTML/XML | lxml |
| CSV | csv/pandas |
| Unsupported | reject or manual |

PDF 主解析器锁定为 **MinerU**。

禁止：

```text
所有 PDF -> extract_text() -> RAG
```

## 14.2 Pipeline

```text
Upload
 -> MIME/size/hash
 -> Malware scan
 -> MinIO raw
 -> document_version
 -> Parser Router
 -> Layout/Page/Table
 -> Normalized Blocks
 -> Chunk
 -> AI-X Claim Draft
 -> Evidence Draft
 -> ACL attach
 -> BM25 + Dense
 -> citation_ready gate
```

## 14.3 Chunk Metadata

必须包含：

- chunk_id
- document_id
- document_version_id
- root_evidence_id
- page_start
- page_end
- section
- content
- content_hash
- source_level
- tenant_id
- owner_id
- visibility_scope
- license_policy_id
- symbol
- available_at
- external_model_allowed

---

# 15. 五路检索

统一 RetrievalService。

## 15.1 Structured

- PostgreSQL
- Redis
- XTQuant
- Snapshot

用于：

- 数字
- 行情
- 正式评分
- 风险
- 订单状态

## 15.2 BM25

Milvus Sparse / BM25。

用于：

- 合同编号
- 标题
- 产品名
- 处罚词
- 日期
- 金额

## 15.3 Dense

Milvus Dense。

用于：

- 财务质量
- 增长逻辑
- 风险传导
- 语义问题

## 15.4 Graph

Neo4j。

用于：

- 客户
- 供应商
- 产品
- 订单
- 合同
- 风险路径

## 15.5 Memory

PostgreSQL Research Snapshot。

用于：

- 上次结论
- 历史变化
- 继续追问

---

# 16. Retrieval Pipeline

```text
Query
 -> Intent/Subquery
 -> Authorization Prefilter
 -> Structured / BM25 / Dense / Graph / Memory
 -> RRF
 -> Root Evidence Dedup
 -> Reranker
 -> Authority Correction
 -> Freshness Correction
 -> Version Correction
 -> ACL Postcheck
 -> Evidence Pack
```

硬规则：

- 精确数字只走 Structured
- Structured 查不到 => 返回“无可靠结构化数据”
- 禁止从 RAG 猜数字
- Milvus 检索前 ACL filter
- 同一文档最多 3 Chunk
- 同一 Root Evidence 最多 2 Chunk
- 同一研报最多 2 Chunk
- Evidence Pack 带 `as_of`

预算：

```yaml
quick:
  lexical_candidates: 12
  dense_candidates: 12
  rerank_input: 16
  final_evidence: 12

standard:
  lexical_candidates: 30
  dense_candidates: 30
  rerank_input: 40
  final_evidence: 24

deep:
  lexical_candidates: 60
  dense_candidates: 60
  rerank_input: 80
  final_evidence: 48

major_risk:
  lexical_candidates: 40
  dense_candidates: 30
  rerank_input: 50
  final_evidence: 24
```

---

# 17. Engine / Skill / Agent / Policy

## Engine

负责确定性：

- Snapshot
- Score
- Risk
- Decision
- Formula
- Statistics

可复现要求：

```text
same input
+ same data version
+ same module version
= same formal result
```

## Skill

权限化能力入口。

示例：

```yaml
name: market_intelligence
version: 1.0.0
execution_type: deterministic_engine

required_scopes:
  - skill.market.execute

allowed_agents:
  - research

data_scopes:
  - MARKET_PUBLIC
  - PUBLIC_EVIDENCE

external_model_allowed: false
side_effect: NONE

budgets:
  timeout_seconds: 8
  max_retries: 1
  max_rows: 500
  max_calls: 3

policy:
  bind_fields:
    - tenant_id
    - user_id
    - task_id
    - symbol
    - as_of
    - purpose
  on_system_degraded: RETURN_STALE_WITH_DISCLOSURE
```

## Agent

负责：

- 理解
- 规划
- 受控 Skill
- 综合解释
- 报告
- 审核

禁止：

- 任意 SQL
- 改评分
- 绕过 Risk
- 扩 TopK
- 改授权
- 正式发布图谱
- 直接发送通知

## Policy

确定性：

```text
ALLOW
REVIEW
DENY
```

---

# 18. Agent-Skill 白名单

| Agent | Allow | Deny |
|---|---|---|
| Document | document_parse, table_extract, claim_draft, evidence_index_draft | 正式 Claim、Graph Publish、Report Send |
| Research | fundamental, technical, market, retrieval, supply_chain, risk_read, scenario_request | SQL、扩大 TopK、改评分、正式发布 |
| Report | snapshot_read, citation, report_render_draft | 重算指标、忽略 Risk、通知 |
| Review | report_read, evidence_check, policy_preview | 改正式状态、发送、删除证据 |

---

# 19. Model Gateway

唯一 DeepSeek 出口。

```text
Agent
 -> Model Gateway
 -> Egress Policy
 -> Redaction
 -> Alias Resolution
 -> Budget
 -> Timeout / Retry / Circuit Breaker
 -> DeepSeek
 -> JSON Schema
 -> One Controlled Repair
 -> Audit / Usage
```

逻辑 Alias：

- fast
- research
- review
- fallback

禁止 Agent 代码硬编码实际模型名。

记录：

- alias
- actual_model
- prompt_version
- schema_version
- task_id
- request_id
- input_tokens
- output_tokens
- latency
- estimated_cost
- retry_count
- cache_hit
- provider_request_id

失败：

- Schema 失败一次受控修复
- 再失败 => downgrade / HITL
- research 不可用 => fallback
- fallback 降低 Confidence
- fallback 不能自动形成重大正式结论
- `external_model_allowed=false` 禁止出网

---

# 20. LangGraph

## 20.1 State

```python
class ResearchGraphState(TypedDict):
    task_id: str
    tenant_id: str
    user_id: str
    symbol: str
    as_of: datetime
    mode: Literal["quick", "standard", "deep"]
    purpose: str

    intent: dict
    module_snapshots: dict
    evidence_pack: list

    risk_snapshot: dict | None
    opportunity_snapshot: dict | None
    decision_snapshot: dict | None

    report_draft: dict | None
    review_result: dict | None
    policy_decision: str | None

    current_stage: str
    retries: dict
    budget: dict
    warnings: list[str]
```

## 20.2 Workflow

```text
START
 -> Intent Router
 -> Stock Identity
 -> Entitlement / Policy
 -> Parallel:
      Fundamental
      Technical
      Market
      Supply Chain
 -> Evidence Pack
 -> Risk & Scenario
 -> Opportunity
 -> Decision Engine
 -> Report Agent
 -> Review Agent
 -> Policy Engine
      ALLOW  -> Outbox
      REVIEW -> HITL
      DENY   -> STOP
 -> DONE
```

## 20.3 Checkpoint

持久化：

- intent_resolved
- modules_completed
- evidence_ready
- decision_ready
- report_drafted
- review_completed
- hitl_waiting
- publication_pending

禁止保存模型私有思考过程。

---

# 21. HITL

## 21.1 Trigger

以下触发人工：

- Policy = REVIEW
- 高风险阈值
- Evidence Gate UNKNOWN
- CONFLICTED
- 关键 Claim 只有 AI-X
- 重大订单/供应链正式发布
- 高风险报告
- 引用/结论不一致
- fallback + 重大正式结论
- 高危管理员操作

## 21.2 状态

```text
DRAFT
 -> REVIEW_REQUIRED
 -> UNDER_REVIEW
      -> APPROVED
      -> NEEDS_REVISION -> DRAFT
      -> REJECTED
 -> PUBLISH_PENDING
 -> PUBLISHED
```

## 21.3 API

```text
GET  /api/v1/reviews/queue
GET  /api/v1/reviews/{review_id}
POST /api/v1/reviews/{review_id}/decision
```

## 21.4 Audit

记录：

- reviewer
- before_version
- after_version
- decision
- reason_code
- duration
- timestamp
- evidence
- report_version

---

# 22. HITL / 产品质量指标

定义：

- review_approval_rate
- agent_suggestion_acceptance_rate
- partial_acceptance_rate
- human_override_rate
- evidence_correction_rate
- report_rework_rate
- review_turnaround_seconds
- hitl_timeout_rate
- false_positive_risk_rate
- false_negative_risk_rate
- user_report_open_rate
- user_export_rate

用途：

- 产品质量
- Agent 评估
- Review 效率
- 灰度判断

禁止直接反向修改正式 Risk Score。

---

# 23. API 规范

统一：

```text
/api/v1
```

## Auth

```text
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /users/me
```

## Research

```text
POST /research/tasks
GET  /research/tasks/{id}
GET  /research/tasks/{id}/events
GET  /research/tasks/{id}/report
```

## Stock

```text
GET /stocks/{symbol}/snapshot
```

## Reports

```text
GET  /reports
GET  /reports/{id}
POST /reports/{id}/export
```

## Files

```text
POST   /files
GET    /files/{id}
DELETE /files/{id}
```

## Review

```text
GET  /reviews/queue
GET  /reviews/{id}
POST /reviews/{id}/decision
```

## Admin

- users
- roles
- permissions
- plans
- data-sources
- audit

## Health

```text
/health/live
/health/ready
/metrics
```

---

# 24. Research Task Contract

Request：

```json
{
  "symbol": "600519.SH",
  "mode": "standard",
  "as_of": "2026-08-21T14:30:00+08:00",
  "modules": [
    "fundamental",
    "technical",
    "market",
    "supply_chain",
    "risk"
  ],
  "question": "当前主要风险和变化是什么？"
}
```

Header：

```text
Idempotency-Key: UUID
```

Response：

```json
{
  "request_id": "req_xxx",
  "task_id": "task_xxx",
  "status": "QUEUED"
}
```

HTTP：

```text
202 Accepted
```

---

# 25. SSE

事件：

```json
{
  "event_id": "evt_xxx",
  "sequence_no": 16,
  "task_id": "task_xxx",
  "type": "stage_progress",
  "stage": "evidence_retrieval",
  "progress": 0.65,
  "message": "正在校验证据",
  "created_at": "2026-08-21T14:31:22+08:00"
}
```

规则：

- SSE 不传 Chain-of-Thought
- 支持 Last-Event-ID
- PostgreSQL workflow_event 是真相源
- Redis 仅辅助
- Event 去重
- Sequence 校验

---

# 26. API 响应与错误

成功：

```json
{
  "request_id": "req_xxx",
  "data": {}
}
```

错误：

```json
{
  "request_id": "req_xxx",
  "error": {
    "code": "EVIDENCE_NOT_READY",
    "message": "可靠证据不足，无法形成正式结论",
    "details": {}
  }
}
```

首批错误码：

- AUTH_INVALID_CREDENTIALS
- AUTH_SESSION_REVOKED
- PERMISSION_DENIED
- ENTITLEMENT_LIMIT_EXCEEDED
- SKILL_NOT_ALLOWED
- DATA_SCOPE_DENIED
- EXTERNAL_MODEL_DENIED
- TASK_NOT_FOUND
- TASK_CONFLICT
- EVIDENCE_NOT_READY
- EVIDENCE_CONFLICTED
- STRUCTURED_DATA_NOT_FOUND
- MODEL_UNAVAILABLE
- MODEL_SCHEMA_INVALID
- SYSTEM_DEGRADED
- RATE_LIMITED
- FILE_TYPE_NOT_ALLOWED
- FILE_TOO_LARGE
- FILE_SECURITY_REJECTED

禁止返回 Python Traceback。

---

# 27. 身份与会话

## Access Token

JWT：

- TTL 10–15 min
- aud
- iss
- sub
- jti
- tenant
- scopes

## Refresh

- opaque random token
- HttpOnly
- Secure
- SameSite
- 7–30 days
- rotation
- reuse detection

Reuse：

1. revoke token family
2. revoke sessions
3. security audit
4. force re-login

## MFA

ADMIN / REVIEWER / OPS 强制：

- TOTP
- WebAuthn

---

# 28. RBAC + ABAC + Entitlement

## RBAC

职责。

## ABAC

属性：

### Subject

- tenant_id
- user_id
- role
- plan
- mfa_level

### Resource

- visibility_scope
- owner_id
- license_policy_id
- symbol
- document_type

### Task

- purpose
- task_id
- as_of
- requested_mode

### Environment

- ip_risk
- device_trust
- system_health
- business_hours

### Model

- external_model_allowed
- quote_allowed
- export_allowed

### Result

- risk_level
- evidence_gate
- side_effect_type

---

# 29. Outbox

事务：

```text
BEGIN
  change business state
  insert outbox_event(effect_key UNIQUE)
COMMIT
```

Worker：

```text
claim
 -> perform side effect
 -> receipt
 -> sent
```

要求：

- worker 可至少一次消费
- 用户可见副作用有效一次
- effect_key 唯一
- retry 不重复通知/报告/Graph

---

# 30. 前端工程规范

## 30.1 架构

采用：

```text
features/
+
shared infrastructure
```

不是：

```text
all business -> views/components/stores
```

## 30.2 P0

创建：

- app
- api
- router
- layouts
- features/auth

## P1

创建：

- features/stock
- features/technical
- features/market
- charts/kline
- charts/market

## P2

创建：

- features/fundamental
- features/risk
- features/report
- charts/financial
- charts/risk

## P3

创建：

- features/files
- features/evidence

## P4

创建：

- features/supply-chain
- charts/graph

## P5

创建：

- features/review
- features/admin

禁止 P0 建全部空壳。

---

# 31. 前端状态

## Global Pinia

仅：

- current user
- permission
- entitlement
- app/system status
- global notification

## Feature Store

例如：

- research task
- review queue
- watchlist

## Local

- dialog
- tab
- dropdown
- local sort/filter

使用 ref/reactive。

禁止所有 API Data 都塞进 Pinia。

---

# 32. Frontend API Layer

```text
FastAPI Pydantic
   ↓
OpenAPI
   ↓
packages/api-types
   ↓
src/api/generated
   ↓
feature API wrapper
   ↓
Vue components
```

Generated 禁止手改。

---

# 33. Frontend SSE

统一：

```text
src/services/sse/
├─ sse-client.ts
├─ research-events.ts
├─ reconnect-policy.ts
└─ types.ts
```

负责：

- reconnect
- Last-Event-ID
- heartbeat
- duplicate detection
- sequence check
- auth recovery
- complete cleanup

---

# 34. Frontend Permission

三层 UI 控制：

## Route Guard

- auth
- permission
- entitlement

## Component Gate

例如：

```text
PermissionGate
EntitlementGate
```

## Backend Final Check

所有安全必须后端再次验证。

前端权限仅用于体验控制。

---

# 35. ECharts

统一：

```text
src/charts/
```

模块：

- kline
- financial
- market
- risk
- graph

公共处理：

- resize
- loading
- empty
- error
- dispose
- theme

---

# 36. Evidence UI

Evidence 作为一级 Feature：

- EvidenceCitation
- EvidenceDrawer
- EvidenceSourceBadge
- EvidenceLevelBadge
- EvidenceConflictAlert

报告引用可展开：

- 来源
- 证据等级
- 页码
- section
- disclosed_at
- available_at
- revision
- 原文

---

# 37. Review UI

Review：

- Queue
- Detail
- Claim Comparison
- Evidence Check
- Risk Comparison
- Report Diff
- Decision Panel
- Audit Timeline

人工审核必须能同时看到：

```text
Agent Conclusion
+ Engine Snapshot
+ Evidence
+ Risk
+ Review Agent
+ Human Decision
```

---

# 38. Design Tokens

P0 至少：

```text
styles/
├─ tokens.css
├─ variables.css
├─ reset.css
└─ element-plus-overrides.scss
```

统一：

- spacing
- font
- radius
- layout
- chart size
- status
- risk severity

---

# 39. 安全

必须：

- Nginx 只暴露 443
- DB/Redis/MinIO/Milvus/Neo4j 不公网暴露
- TLS
- CORS allowlist
- CSRF
- Rate Limit
- MIME/size/ext 校验
- Malware Scan
- Zip Bomb Protection
- SSRF
- XSS
- SQL Injection Protection
- IDOR/Cross-Tenant Test
- Private Document ACL
- Log Redaction
- Secret Scan
- SBOM
- pip-audit
- npm audit
- Container Scan

---

# 40. 可观测性

## SLO

| Indicator | Target |
|---|---|
| Web/API availability | >=99.9% |
| Normal API P95 | <=500ms |
| Login/Auth P95 | <=300ms |
| Quick Research P95 | <=20s |
| Standard Research P95 | <=90s |
| Standard Retrieval P95 | <=1.5s |
| Major Risk Retrieval P95 | <=2.0s |
| Cross-tenant unauthorized recall | 0 |
| Duplicate visible side effects | 0 |
| PostgreSQL RPO | <=15min |
| PostgreSQL RTO | <=4h |

## Trace

```text
Browser
 -> Nginx
 -> FastAPI
 -> Celery
 -> LangGraph
 -> Skill
 -> Engine/Retrieval
 -> DeepSeek
 -> PostgreSQL
```

统一 request_id。

## Metrics

- QPS
- error rate
- latency
- queue depth
- task duration
- task failure
- retry
- SSE count
- model tokens
- cost
- schema failure
- retrieval empty
- retrieval latency
- ACL deny
- HITL pending
- HITL timeout
- MiniQMT heartbeat
- data freshness
- outbox backlog

---

# 41. 测试布局

## Backend

```text
apps/backend/tests/
├─ unit/
└─ api/
```

## Collector

```text
apps/xtquant-collector/tests/unit/
```

## Web

```text
apps/web/tests/
├─ unit/
├─ component/
└─ fixtures/
```

## Root

```text
tests/
├─ integration/
├─ e2e/
├─ retrieval/
├─ risk_replay/
├─ security/
└─ performance/
```

---

# 42. 测试要求

## Backend Unit

- Engine
- Formula
- Policy
- Permission
- State Machine
- Outbox
- Refresh Rotation
- PIT

## Integration

- PostgreSQL
- Redis
- MinIO
- Milvus
- Neo4j

## Retrieval Golden Dataset

- Recall@K
- MRR
- nDCG
- Root Evidence
- Citation Ready
- ACL leak = 0
- Future Leakage = 0
- Wrong Revision = 0

## Agent

- fixed input
- schema
- whitelist
- forbidden tool
- loop budget
- malformed output
- fallback
- review trigger

## Risk Replay

- WATCH
- RESTRICT
- BLOCK

## Security

- OWASP
- IDOR
- CSRF
- XSS
- SSRF
- File Attack
- Cross Tenant
- Unauthorized Research Report Retrieval

## Performance

- Locust/k6
- API
- SSE
- Queue
- Retrieval

---

# 43. 灰度发布

所有必须版本化：

- backend image
- frontend
- engine
- prompt
- model alias config
- retrieval config
- reranker
- graph workflow
- policy

## Feature Flag

表：

- feature_flag
- feature_flag_rule
- feature_flag_exposure

支持：

- environment
- tenant allowlist
- user allowlist
- percentage
- kill switch
- start/end

## Canary

```text
shadow
 -> internal 1%
 -> 5%
 -> 20%
 -> 50%
 -> 100%
```

重大 Prompt / Model / Retrieval 变化先 Shadow。

## Zero Tolerance

立即停止：

- cross-tenant leak > 0
- unauthorized recall > 0
- future leakage > 0
- wrong revision overwrite > 0
- duplicate formal side-effect > 0
- Risk BLOCK bypass > 0

其他回滚触发：

- API error
- P95 degradation
- task failure
- model schema failure
- HITL spike
- evidence correction spike
- cost/task spike

阈值配置化。

---

# 44. CI/CD

PR：

### Python

```text
ruff
mypy
pytest unit/api
bandit
pip-audit
```

### Web

```text
eslint
prettier check
typecheck
vitest
```

### Contract

```text
OpenAPI export
TS generation
diff check
```

### Security

```text
secret scan
dependency scan
```

Main：

- integration
- Playwright smoke
- migration test
- Docker build
- SBOM
- image scan

RC：

- full integration
- retrieval golden
- risk replay
- security negative
- performance
- backup/restore

---

# 45. 生产部署

## Web

Nginx/CDN 静态。

## API / Worker

Linux Containers。

## XTQuant Collector

Windows Host。

仅通过：

- outbound HTTPS
- authenticated API
- queue（如后续引入）

与生产平台通信。

## Storage

- PostgreSQL PITR
- MinIO Versioning / Replication
- Milvus Rebuild Script
- Neo4j Rebuild Script

生产与测试：

- Account separated
- Key separated
- DB separated
- Bucket separated

---

# 46. P0-P6 实施路线

# P0 基础骨架

目标：

- Monorepo
- Vue
- FastAPI
- uv/pnpm
- PostgreSQL/Redis/MinIO
- Health
- Auth 基座
- Contract
- CI

任务：

- C0-001 Monorepo
- C0-002 Infrastructure
- C0-003 FastAPI Skeleton
- C0-004 SQLAlchemy/Alembic
- C0-005 Authentication
- C0-006 RBAC/ABAC/Entitlement
- C0-007 Workflow Event Store
- C0-008 Outbox Base
- C0-009 Vue Skeleton
- C0-010 OpenAPI -> TS
- C0-011 CI

P0 Gate：

- login
- permission negative
- migration
- health
- contract
- CI

---

# P1 行情 / Technical / Market

- C1-001 Collector Skeleton
- C1-002 SQLite/WAL
- C1-003 Ingest API
- C1-004 Market Schema
- C1-005 Redis Hot Snapshot
- C1-006 PostgreSQL Minute State
- C1-007 Stock Identity Skill
- C1-008 Realtime Snapshot Skill
- C1-009 Technical Engine
- C1-010 Market Engine
- C1-011 Snapshot API
- C1-012 Web UI
- C1-013 Reconnect/Gap Tests

Gate：

- reconnect
- replay idempotency
- freshness visible
- stale visible
- snapshot reproducible

---

# P2 Fundamental / Risk / Report

- C2-001 financial_fact
- C2-002 PIT Resolver
- C2-003 Fundamental
- C2-004 CPA/Quality
- C2-005 Peer
- C2-006 Valuation
- C2-007 Risk
- C2-008 Scenario
- C2-009 Decision
- C2-010 Snapshot
- C2-011 Standard Research
- C2-012 Report
- C2-013 Risk Replay

Gate：

- PIT
- reproducibility
- risk audit
- no LLM guessed numbers

---

# P3 Document / Evidence / Retrieval

- C3-001 Upload
- C3-002 MinIO Raw
- C3-003 File Security
- C3-004 Parser Router
- C3-005 MinerU
- C3-006 DOCX
- C3-007 XLSX
- C3-008 HTML
- C3-009 Normalized Block
- C3-010 Chunk
- C3-011 Evidence/Claim Draft
- C3-012 BM25
- C3-013 Dense
- C3-014 ACL
- C3-015 RRF
- C3-016 Reranker
- C3-017 Evidence Pack
- C3-018 Citation UI/API
- C3-019 Golden Dataset

Gate：

- page citation
- private ACL 0 leakage
- no RAG guessed structured numbers
- retrieval quality gate

---

# P4 Supply Chain

- C4-001 Contract/Order
- C4-002 Lifecycle
- C4-003 Claim Extraction
- C4-004 Entity Alias
- C4-005 Graph Candidate
- C4-006 Graph Review
- C4-007 Neo4j Publish
- C4-008 Graph ACL
- C4-009 Supply Chain Skill
- C4-010 Risk Propagation
- C4-011 Graph UI

Gate：

- Edge binds Evidence
- Edge valid time/status
- Draft Claim not formal
- Order lifecycle correct

---

# P5 Multi-Agent / HITL

- C5-001 Model Gateway
- C5-002 Model Discovery
- C5-003 Prompt Registry
- C5-004 Skill Manifest
- C5-005 Skill Gateway
- C5-006 Intent Router
- C5-007 Document Agent
- C5-008 Research Agent
- C5-009 Report Agent
- C5-010 Review Agent
- C5-011 LangGraph
- C5-012 Checkpoint
- C5-013 Policy
- C5-014 Human Review
- C5-015 Review UI
- C5-016 HITL Metrics
- C5-017 Outbox Publish
- C5-018 Agent Security Tests

Gate：

- tool whitelist
- policy non-bypass
- Review PASS != publish
- HITL audit
- acceptance metrics

---

# P6 Production Readiness

- C6-001 OTel
- C6-002 Prometheus
- C6-003 Grafana
- C6-004 Alerts
- C6-005 Backup/PITR
- C6-006 MinIO Versioning
- C6-007 Milvus Rebuild
- C6-008 Neo4j Rebuild
- C6-009 Security
- C6-010 Performance
- C6-011 Feature Flag
- C6-012 Canary
- C6-013 Rollback
- C6-014 DR Drill
- C6-015 Production Checklist

Gate：

- performance
- security
- restore
- SLO
- canary
- rollback
- joint sign-off

---

# 47. P0 第一轮 Codex 执行边界

第一轮只执行：

```text
C0-001
C0-002
C0-003
```

允许创建：

- apps/web
- apps/backend
- apps/xtquant-collector
- packages/api-types
- packages/shared-contracts
- infrastructure
- tests
- docs
- scripts
- .github

Backend 第一轮只需要：

```text
stock_research/
├─ main.py
├─ api/
├─ core/
└─ observability/
```

禁止第一轮提前创建大量：

- agents
- graphs
- skills
- engines
- retrieval
- documents
- policies

---

# 48. P0 第一轮 Codex 指令

```text
执行 C0-001、C0-002、C0-003。

严格遵守本 V2.0 技术方案。

目标：

1. 初始化 stock-research-platform Monorepo。
2. Backend：FastAPI + Python 3.10 + uv。
3. Backend 使用 apps/backend/src/stock_research。
4. Alembic 放 apps/backend/migrations。
5. Backend tests 使用 tests/unit 和 tests/api。
6. XTQuant Collector 使用：
   apps/xtquant-collector/src/xtquant_collector。
7. 根目录建立 uv workspace。
8. Web 使用 Vue 3 + Vite + TypeScript + pnpm workspace。
9. 建立 packages/api-types。
10. 建立 packages/shared-contracts。
11. REST 契约唯一来源是 FastAPI/Pydantic -> OpenAPI。
12. api-types 从 OpenAPI 自动生成。
13. shared-contracts 只放错误码、公共 enum、SSE schema、Feature Flag。
14. 建立 export_openapi。
15. 建立 api-types generation。
16. CI 做 contract diff。
17. 建 PostgreSQL / Redis / MinIO。
18. Backend 提供 /health/live。
19. Backend 提供 /health/ready。
20. 实现 request_id middleware。
21. 实现 structlog。
22. 配置 ruff / mypy / pytest / Vitest / ESLint / Prettier。
23. 不实现业务分析。
24. 不接 DeepSeek。
25. 不接 XTQuant。
26. 不创建 Agent/Skill/Engine 空业务模块。

完成后执行：

uv sync
uv run ruff check .
uv run mypy .
uv run pytest
pnpm install
pnpm test
docker compose up -d

验证：

GET /health/live
GET /health/ready

完成后停止，不继续 C0-004。
```

---

# 49. Codex 单任务执行协议

每次：

1. 读取 V2.0。
2. 检查仓库状态。
3. 只做指定 Task。
4. 不破坏既有实现。
5. 不擅自改架构。
6. 新 Schema 同步：
   ORM / Pydantic / Migration / Test
7. 新 API 同步：
   OpenAPI / Auth / Error / request_id / Test
8. 新 Skill 同步：
   Manifest / Permission / Whitelist / Audit / Budget / Test
9. 模型调用只能 Model Gateway。
10. 副作用只能 Outbox。
11. 跨租户访问必须负向测试。
12. 完成后运行 lint/type/test。

---

# 50. Codex 完成报告模板

```markdown
## Task
C?-???

## Implemented
- ...

## Changed Files
- ...

## Database Migrations
- ...

## API Changes
- ...

## Tests
- command:
- result:

## Security / Permission Checks
- ...

## Known Limitations
- ...

## Next Suggested Task
- ...
```

禁止只说“已完成”。

---

# 51. Codex 禁止事项

- 禁止 DeepSeek Key 入前端
- 禁止 Secret 入 Git
- 禁止 Agent 任意 SQL
- 禁止 LLM 正式数字落库
- 禁止 Redis 做真相源
- 禁止跳过 Migration
- 禁止私有文档公共向量化
- 禁止 RAG 猜结构化数字
- 禁止 Review Agent 自己批准发布
- 禁止 CoT 入 SSE/日志
- 禁止关闭 tenant filter
- 禁止巨型 PR 一次 P0-P6
- 禁止无测试重构 Permission/Risk/Outbox
- 禁止吞数据冲突
- 禁止把订单/合同/收入/回款混为一体

---

# 52. 最终生产验收清单

- [ ] Frontend 无 DeepSeek/DB/XTQuant/MinIO Secret
- [ ] API 均有 OpenAPI
- [ ] API 统一 Error Code
- [ ] Sensitive API 全鉴权
- [ ] Research POST 有 Idempotency-Key
- [ ] 所有 Response 可追 request_id
- [ ] Refresh Rotation / Reuse Detection
- [ ] MFA 高权限通过
- [ ] RBAC/ABAC/Entitlement Negative Test
- [ ] Skill Default Deny
- [ ] USER_PRIVATE Cross Tenant Recall = 0
- [ ] Redis 清空可恢复
- [ ] Structured Missing 不从 RAG 猜数
- [ ] BM25 + Dense + RRF + Reranker + ACL Golden Dataset
- [ ] Neo4j Edge 绑定 Evidence/Time/Status/Auth/Review
- [ ] Model Gateway 可观测 Token/Cost/Latency
- [ ] Quick/Standard SLO
- [ ] Timeout Safe Degrade
- [ ] Outbox 无重复可见副作用
- [ ] MiniQMT Disconnect Replay
- [ ] PostgreSQL PITR
- [ ] Milvus Rebuild
- [ ] Neo4j Rebuild
- [ ] File/SSRF/XSS/CSRF/IDOR Test
- [ ] Prompt/Model/Retrieval Canary + Rollback
- [ ] HITL 全链路审计
- [ ] HITL Acceptance/Override/Rework 可观测
- [ ] Technical/Data/Security/Compliance/Ops Sign-off

---

# 53. Single Source of Truth 规则

从 V2.0 起：

```text
V2.0 = Architecture + Engineering + Codex Execution Baseline
```

以下文档不得与 V2.0 冲突：

- AGENTS.md
- ARCHITECTURE.md
- CODEX_TASKS.md
- README
- ADR
- CI config
- Deployment Runbook

如果未来必须改变核心架构：

1. 创建 ADR。
2. 评审。
3. 更新 V2.x。
4. 更新 AGENTS/ARCHITECTURE/CODEX_TASKS。
5. 再允许 Codex 实施。

Codex 不得自行改变：

- 前后端分离
- PostgreSQL 真相源
- OpenAPI 真相源
- Engine 正式数字
- Data Trust
- ACL before retrieval
- Skill Gateway
- Policy + Outbox
- HITL
- P0-P6 阶段边界

---

# 54. 最终生产定义

只有当 P0-P6 全部门禁通过，系统才能定义为：

**Production Ready**

以下均不等于生产就绪：

- 页面能打开
- DeepSeek 能回复
- MiniQMT 能取行情
- LangGraph 能运行
- 报告能生成

生产就绪的判断：

```text
可复现
+ 可授权
+ 可审计
+ 可引用
+ 可恢复
+ 可降级
+ 可灰度
+ 可回滚
+ 零跨租户未授权召回
+ 零重复正式副作用
```
