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
- [x] C1-002 SQLite/WAL（采集器本地 `collector-local-wal.sqlite` 持久化缓冲，不替代 PostgreSQL 真相源）
- [x] C1-003 Ingest API（`POST /api/v1/ingest/events`，事件幂等写入 `inbox_event`）
- [x] C1-004 WAL -> Ingest Transport（`WALPump` 批量推送、成功后标记 sent、失败保留 pending）
- [x] C1-005 XTQuant 行情采集适配（`subscribe_quote` 回调 -> 标准化 `QuoteEvent` -> WAL）
- [x] C1-006 Inbox -> Market Snapshot Consumer（消费 `inbox_event` 写入 `market_snapshot`，后台轮询）
- [x] C1-007 Market Snapshot Summary（`GET /market/snapshots/{symbol}/summary` 确定性摘要分析）
- [x] C1-008 前端行情展示（Vue 行情页接入快照列表/摘要 API）
- [x] C1-009 行情页自动刷新与价格走势图（ECharts）
- [x] C1-010 多标的行情监控（添加/移除标的、摘要卡片、选中切换）
- [x] C1-011 历史 K 线聚合与行情异常状态提示（后端 bars API + 前端 K 线图/状态横幅）
- [x] C1-012 XTQuant 历史 K 线直落标准 bar（`market_bar` + 采集器 `XtQuantBarFetcher`）
- [x] C1-013 K线成交量副图与采集周期配置校验
- [x] C1-014 MA/EMA 技术指标与成交量均量线
- [x] C1-015 MACD/RSI 指标与参数配置
- [x] C1-016 指标显示开关与参数模板
- [x] C1-017 指标参数本地持久化与更多预设模板
- [x] C1-018 指标参数导入/导出与图表主题切换
- [x] C1-019 多套命名配置方案管理
- [x] C1-020 方案重命名与默认启动配置
- [x] C1-021 配置方案整体备份/导入
- [x] C1-022 指标配置云端同步与更多图表主题
- [x] C1-023 云端同步冲突提示与自定义主题颜色
- [x] C1-024 云端冲突精细处理（保留本地/使用云端/合并方案）
- [x] C1-025 冲突自动合并规则配置
- [x] C1-026 冲突合并结果预览
- [x] C1-027 冲突历史记录
- [x] C1-028 冲突历史导出
- [x] C1-029 冲突历史导入/归档
- [x] C1-030 冲突历史自动清理策略
- [x] C1-031 归档自动清理策略
- [x] C1-032 Redis Hot Snapshot（行情摘要热读缓存，PostgreSQL 真相源）
- [x] C1-033 PostgreSQL Minute State（`market_minute_state` 一分钟粒度状态投影）
- [x] C1-034 Stock Identity Skill（股票代码 / 市场确定性规范化）
- [x] C1-035 Realtime Snapshot Skill（实时快照读取与 stale 标记）
- [x] C1-036 Technical Engine / Market Engine（确定性引擎边界）
- [x] C1-037 Reconnect / Gap Tests（WAL 失败重试、行情缺口检测测试）

P1 完成：V2.0 P1 规范任务与 Gate 已补齐，可正式进入 P2。

## P2 Fundamental / Risk / Report

- [x] C2-001 financial_fact（点时间财务事实存储）
- [x] C2-002 PIT Resolver（按 as_of 解析最新可用口径）
- [x] C2-003 Fundamental（PIT 财务事实 -> 确定性基本面快照与比率）
- [x] C2-004 CPA/Quality
- [x] C2-005 Peer
- [x] C2-006 Valuation
- [x] C2-007 Risk（财务杠杆 / 流动性 / 现金流覆盖 / 波动回撤风险）
- [x] C2-008 Scenario（估值场景目标价 / 隐含涨跌幅）
- [x] C2-009 Decision（Risk + Scenario -> AVOID / HOLD / ATTRACTIVE）
- [x] C2-010 Snapshot（统一聚合各确定性引擎快照）
- [x] C2-011 Standard Research（统一快照 + 同业比较研究服务）
- [x] C2-012 Report（确定性结构化报告渲染）
- [x] C2-013 Risk Replay（多时点 PIT 风险回放与可复现性）

## P3 Document / Evidence / Retrieval

- [x] C3-001 Upload（文件上传、原始内容写入 MinIO、Document/Version 落库）
- [x] C3-002 MinIO Raw（原始对象读取 / 存在性 / 删除回源）
- [x] C3-003 File Security（大小 / 扩展名白名单 / 哈希校验）
- [x] C3-004 Parser Router（扩展名 -> MinerU/docx/xlsx/html/csv）
- [x] C3-005 MinerU（CLI 适配器 / 可用性检测 / Markdown 输出）
- [x] C3-006 DOCX（python-docx 段落解析适配器）
- [x] C3-007 XLSX（openpyxl 工作表解析适配器）
- [x] C3-008 HTML（lxml 文本提取适配器）
- [x] C3-009 Normalized Block（归一化块模型 / 迁移 / 构建器 / Store）
- [x] C3-010 Chunk（确定性文本分块 / 重叠窗口 / 哈希）
- [x] C3-011 Evidence/Claim Draft（DRAFT 状态模型 / Store / 引用绑定）
- [x] C3-012 BM25（确定性稀疏检索索引 / 查询）
- [x] C3-013 Dense（余弦相似度稠密向量索引）
- [x] C3-014 ACL（检索前默认拒绝 / 租户可见范围 license symbol 过滤）
- [x] C3-015 RRF（多路排序 Reciprocal Rank Fusion）
- [x] C3-016 Reranker（词法重排 / 权威 / 新鲜度）
- [x] C3-017 Evidence Pack（排序 / 根证据去重 / 数量上限 / as_of）
- [x] C3-018 Citation API（按文档列证据 / 按 ID 取证据）
- [x] C3-019 Golden Dataset（Recall@K / MRR / ACL 泄漏评估）

## P4 Supply Chain

- [x] C4-001 Contract/Order（合同 / 订单模型与 Store）
- [x] C4-002 Lifecycle（订单状态事件 / 确定性状态流转）
- [x] C4-003 Claim Extraction（规则化供应链关系抽取）
- [x] C4-004 Entity Alias（组织别名模型 / 解析服务）
- [x] C4-005 Graph Candidate（Claim -> 节点 / 边候选）
- [x] C4-006 Graph Review（Evidence 绑定审核）
- [x] C4-007 Neo4j Publish（Cypher 节点 / 边发布服务）
- [x] C4-008 Graph ACL（未授权节点相关边过滤）
- [x] C4-009 Supply Chain Skill（manifest + 文本 -> Graph Candidate）
- [x] C4-010 Risk Propagation（沿边确定性风险传播）
- [x] C4-011 Graph UI（ECharts 供应链图页面）

## P5 Multi-Agent / HITL

- [x] C5-001 Model Gateway（Gateway 抽象 + DeepSeek Client）
- [x] C5-002 Model Discovery（别名注册 / 能力 / 优先级解析）
- [x] C5-003 Prompt Registry（版本化模板注册 / 渲染）
- [x] C5-004 Skill Manifest（统一 Manifest 注册表）
- [x] C5-005 Skill Gateway（默认拒绝 / scope 校验）
- [x] C5-006 Intent Router（规则化意图 -> Agent）
- [ ] C5-007 Document Agent
- [x] C5-008 Research Agent（封装标准研究服务）
- [x] C5-009 Report Agent（封装报告渲染服务）
- [x] C5-010 Review Agent（确定性报告审核）
- [x] C5-011 LangGraph（线性图执行 fallback）
- [x] C5-012 Checkpoint（CheckpointStore 持久化）
- [x] C5-013 Policy（默认 DENY 的确定性 Policy Engine）
- [x] C5-014 Human Review（模型 / 状态流转 / 决策）
- [x] C5-015 Review UI（前端审核页面）
- [x] C5-016 HITL Metrics（审核决策指标计算）
- [x] C5-017 Outbox Publish（正式副作用发布入口 / 幂等）
- [x] C5-018 Agent Security Tests（Skill/Policy/ACL/Graph 安全回归）
