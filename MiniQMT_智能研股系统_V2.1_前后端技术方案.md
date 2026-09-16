# MiniQMT 智能研股系统 V2.1 前后端技术方案

> 文档状态：已确认，待开发  
> 适用范围：股票研究系统前端 + 后端  
> 基线：`MiniQMT_智能研股系统_V2.0_最终技术方案_Codex开发执行版.md`  
> 目标：在现有代码基础上，明确产品逻辑、前端页面、后端架构、数据流和开发顺序

---

## 1. 目标

面向股票研究场景，输入一只股票后，从以下维度完成专业分析：

1. 市场分析
2. 技术面分析
3. 基本面分析
4. 财务分析
5. 估值分析
6. 供应链分析
7. 风险分析
8. 综合研究报告

最终输出一份可解释、可追溯、可审核的综合研究报告。

---

## 2. 产品形态

### 2.1 核心使用流程

```text
用户输入股票代码
    ↓
选择分析模式
    ↓
点击开始分析
    ↓
系统异步执行分析任务
    ↓
SSE 实时推送进度
    ↓
用户查看各维度分析结果
    ↓
查看综合研究报告
    ↓
查看证据引用和人工审核状态
```

### 2.2 顶部导航

最终顶部导航只保留：

```text
工作台
任务历史
审核中心
```

### 2.3 工作台内部 Tab

股票分析工作台内部使用 Tab 展示：

```text
综合报告
市场分析
技术面分析
基本面分析
财务分析
估值分析
供应链分析
风险分析
```

综合报告 Tab 包含：

```text
投资摘要
市场分析结论
技术分析结论
基本面分析结论
财务分析结论
估值与目标价
供应链分析结论
风险分析结论
证据引用
人工审核状态
综合建议
```

---

## 3. 总体技术架构

```text
前端 Vue 3 + Vite + ECharts
    ↓
FastAPI + JWT/RBAC/ABAC 鉴权
    ↓
异步任务 + SSE
    ↓
LangGraph 编排
    ↓
确定性 Engine + 受控 Agent
    ↓
Model Gateway / Skill Gateway / 未来 MCP Gateway
    ↓
PostgreSQL / Redis / Neo4j / Milvus / MinIO
    ↓
标准 RAG / Graph RAG / Agentic RAG
    ↓
综合报告 + 证据引用 + 人工审核
```

核心原则：

```text
能确定性计算的，用 Engine。
能写代码算清楚的，不交给 LLM。
非结构化理解、推理、表达，才用 Agent。
正式副作用必须经过 Outbox。
模型调用必须经过 Model Gateway。
工具调用必须经过 Skill Gateway。
检索前必须完成 ACL。
正式数字不得由 RAG 猜测。
```

---

## 4. 分析模块定义

### 4.1 市场分析

**定位：** 当前股票在市场中如何交易。

输入：

```text
股票代码
时间点 as_of
实时行情快照
历史成交数据
新闻公告
```

输出：

```text
最新价格
涨跌幅
成交量
成交额
换手率
买卖价差
流动性
市场状态
新闻公告摘要
```

实现类型：

```text
确定性 Engine + 数据库读取
```

---

### 4.2 技术面分析

**定位：** 判断价格趋势、周期和拐点。

输入：

```text
K 线周期
历史 K 线
指标参数
```

输出：

```text
MA / EMA
MACD
RSI
成交量均线
趋势判断
支撑位 / 压力位
FFT 主导周期
小波能量分解
LSTM 预测
周期阶段
技术结论
```

实现类型：

```text
确定性 Engine
FFT / 小波 / LSTM 均为算法
```

---

### 4.3 基本面分析

**定位：** 判断公司是不是一门好生意。

输入：

```text
公司信息
行业
商业模式
产品结构
竞争格局
管理层
股东结构
研报、公告、行业资料
```

输出：

```text
行业景气度
商业模式评价
竞争壁垒
成长逻辑
核心优势
核心风险
基本面结论
证据引用
```

实现类型：

```text
受控 Agent + RAG
所有定性结论必须绑定证据
```

---

### 4.4 财务分析

**定位：** 判断公司赚不赚钱、财务是否健康。

输入：

```text
资产负债表
利润表
现金流量表
多个报告期财务事实
```

输出：

```text
营收增长
净利润增长
毛利率
净利率
ROE
ROA
资产负债率
流动比率
速动比率
利息保障倍数
经营现金流
自由现金流
盈利质量
杜邦分析
财务风险点
财务结论
```

实现类型：

```text
确定性 Engine
财务计算不允许 LLM 直接计算
```

基础能力已落地：新增 `ProfessionalFinancialEngine` 和
`POST /api/v1/fundamental/professional`，覆盖同比、速动比率、利息保障倍数、
自由现金流、杜邦分析和财务风险点。

---

### 4.5 估值分析

**定位：** 判断公司值多少钱，当前股价贵不贵。

输入：

```text
财务分析结果
EPS
BVPS
SPS
当前价格
股本
可比公司
增长假设
折现率假设
```

输出：

```text
PE
PB
PS
PEG
EV/EBITDA
DCF / 自由现金流估值
历史估值分位
同行估值对比
BASE / BULL / BEAR 情景
目标价区间
安全边际
估值结论
```

实现类型：

```text
确定性 Engine
```

---

### 4.6 供应链分析

**定位：** 判断公司上下游关系和依赖风险。

输入：

```text
供应商
客户
合同
订单
组织别名
供应链文本
```

输出：

```text
供应链关系图
客户集中度
供应商集中度
关键依赖节点
合同 / 订单状态
风险传播结果
供应链结论
```

实现类型：

```text
Neo4j 图 + 确定性风险传播
文档抽取部分可先使用 Skill / 后续 Agentic RAG
```

---

### 4.7 风险分析

**定位：** 汇聚各专业分析结果，输出统一风险结论。

风险分析是汇聚层：

```text
市场分析 ─────────┐
技术分析 ─────────┤
基本面分析 ───────┤
财务分析 ─────────┼──► 风险分析 ──► 综合报告
估值分析 ─────────┤
供应链分析 ───────┤
新闻公告 ─────────┘
```

输出：

```text
财务风险
市场风险
技术风险
估值风险
供应链风险
事件风险
风险因子列表
综合风险评分
风险等级
风险动作
主要风险说明
数据覆盖度
```

实现类型：

```text
确定性聚合 Engine
不允许 LLM 直接决定风险等级
```

---

### 4.8 综合研究报告

**定位：** 汇总所有分析模块，生成最终报告。

输入：

```text
市场分析结果
技术分析结果
基本面分析结果
财务分析结果
估值分析结果
供应链分析结果
风险分析结果
证据引用
```

输出：

```text
结构化报告章节
中文投资叙述
证据引用
人工审核状态
最终建议
```

实现类型：

```text
工作流组装 + 可选 Agent 润色
审核决策必须由规则 + 人工完成
```

---

## 5. 数据源和数据流

### 5.1 XTQuant

XTQuant 作为独立数据采集器：

```text
XTQuant Collector
    ↓
SQLite WAL 本地缓冲
    ↓
HTTP Ingest API
    ↓
inbox_event
    ↓
PostgreSQL / Redis
```

当前不需要 MCP：

```text
XTQuant 是数据源，不是 Agent 工具。
系统不主动发现 XTQuant。
XTQuant 采集器通过 Ingest Token 推送数据。
```

未来如果外部 Agent 框架需要直接调用 XTQuant，再将 XTQuant 包装为 MCP Server。

### 5.2 PostgreSQL

作为业务真相源：

```text
用户 / 租户 / 角色 / 权限
任务 / 任务版本 / 事件
市场快照 / K 线 / 新闻
财务事实
文档 / 证据 / Claim
合同 / 订单 / 组织别名
人工审核
Outbox
Feature Flag
```

### 5.3 Redis

用于：

```text
热点行情摘要缓存
临时状态
分布式锁
短期缓存
```

PostgreSQL 仍是真相源。

### 5.4 Neo4j

用于：

```text
供应链实体关系图
供应链图查询
风险传播
未来 Graph RAG 关系层
```

Neo4j 是图投影，不是业务真相源。

### 5.5 Milvus

用于：

```text
文档 Dense 向量检索
未来 Sparse / Hybrid 检索
标准 RAG 和 Graph RAG 的向量层
```

### 5.6 MinIO

用于：

```text
原始文档对象存储
文档版本
原始文件不可变版本
```

---

## 6. 后端设计

### 6.1 技术栈

```text
Python 3.10
FastAPI
SQLAlchemy Async
PostgreSQL
Redis
Neo4j
Milvus
MinIO
LangGraph
JWT / Argon2id
```

### 6.2 执行模型

分析任务必须异步：

```text
POST /api/v1/research/tasks
    ↓
创建任务，返回 task_id
    ↓
后台执行 LangGraph DAG
    ↓
SSE 推送执行事件
    ↓
任务状态变化：
queued → running → completed / review_required / failed / rejected
```

### 6.3 LangGraph 编排

LangGraph 负责：

```text
节点调度
依赖管理
并行执行
状态传递
失败重试
Checkpoint
人工审核中断
```

推荐节点：

```text
market_engine                 工作流
technical_engine              工作流
financial_engine              工作流
valuation_engine              工作流
fundamental_agent             Agent
supply_chain_extract_agent    Agent
supply_chain_graph_builder    工作流
news_agent                    Agent
risk_aggregator               工作流
report_compiler               工作流
report_narrative_agent        Agent
review_policy                 工作流
human_review                  HITL
```

### 6.4 Model Gateway

所有 LLM 调用必须经过：

```text
Model Gateway
```

职责：

```text
模型别名解析
模型选择
请求校验
Token 统计
延迟记录
成本估算
未来预算控制
```

### 6.5 Skill Gateway

所有 Agent 工具调用必须经过：

```text
Skill Gateway
```

职责：

```text
默认拒绝
Skill Manifest 注册
scope 权限校验
调用审计
```

当前已有：

```text
Stock Identity Skill
Realtime Snapshot Skill
Supply Chain Skill
Research Context Skill
```

未来扩展：

```text
财务数据读取 Skill
K 线读取 Skill
Neo4j 图查询 Skill
文档证据检索 Skill
估值计算 Skill
风险计算 Skill
新闻读取 Skill
```

### 6.6 未来 MCP Gateway

当前不引入 MCP。

满足以下条件时再引入：

```text
需要接入外部数据商工具
需要跨服务工具复用
需要给其他 Agent 框架提供工具
```

外部 Agent 框架为 MCP Host/Client，XTQuant 包装服务为 MCP Server。

### 6.7 Outbox

正式副作用必须经过 Outbox：

```text
业务事件写入 Outbox
    ↓
后台派发
    ↓
幂等 receipt
    ↓
保证正式副作用可恢复、可重放
```

---

## 7. 前端设计

### 7.1 技术栈

```text
Vue 3
TypeScript
Vite
Pinia
Vue Router
Axios
ECharts
```

### 7.2 页面结构

```text
登录页
DefaultLayout
├── 工作台
├── 任务历史
└── 审核中心
```

工作台内部：

```text
股票代码输入
分析模式选择
开始分析按钮
分析进度
分析结果 Tab
```

### 7.3 工作台交互

用户点击“开始分析”后：

```text
显示任务进度
通过 SSE 更新事件
各 Tab 逐步加载
最终展示综合报告
```

前端需要：

```text
自动刷新 access token
401 单飞刷新
SSE 断线重连
错误提示
任务状态轮询
```

### 7.4 图表展示

```text
行情：价格走势图
技术：K 线、指标、FFT、小波、LSTM
供应链：ECharts 关系图
风险：风险因子表、风险等级
估值：目标价区间、情景对比
```

---

## 8. 鉴权设计

### 8.1 API 鉴权

```text
Access Token：短期 JWT
Refresh Token：HttpOnly Cookie
密码哈希：Argon2id
刷新令牌轮换
刷新令牌复用检测
```

### 8.2 权限模型

```text
RBAC
ABAC
租户隔离
角色权限
数据范围
```

### 8.3 检索权限

```text
ACL-before-retrieval
租户过滤
symbol 许可范围过滤
文档 license 过滤
external_model_allowed 过滤
```

### 8.4 Agent / Skill 权限

```text
Agent Manifest 声明 required_scopes
Skill Gateway 默认拒绝
每次 Skill 调用携带 scope
```

### 8.5 采集器鉴权

```text
XTQuant Collector 使用独立 Ingest Token
不直接使用用户 JWT
```

---

## 9. RAG 设计

### 9.1 标准 RAG

当前已有基础实现，用于：

```text
文档解析
归一化块
分块
Embedding
Milvus / Dense
BM25
混合检索
RRF
Reranker
Evidence Pack
Citation
```

用途：

```text
基本面定性分析
供应链证据提取
新闻公告解读
最终报告证据引用
```

### 9.2 Graph RAG

基础能力已落地：`GraphRagRetriever` 已可从 Neo4j 图边中按查询词召回关系证据。

```text
供应链实体关系问答
跨公司风险传导
关系 + 文档证据联合检索
```

### 9.3 Agentic RAG

基础能力已落地：`AgenticRagService` 已支持确定性多轮查询改写、检索去重和证据链记录。

```text
多跳检索
Agent 自动改写查询
证据链构建
专业基本面分析
```

### 9.4 RAG 边界

```text
结构化数字不允许由 RAG 猜测
财务 / 技术 / 估值 / 风险计算必须走 Engine
```

---

## 10. API 设计

### 10.1 鉴权

```text
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/users/me
```

### 10.2 研究任务

```text
POST /api/v1/research/tasks
GET  /api/v1/research/tasks/{task_id}
GET  /api/v1/research/tasks/{task_id}/versions
GET  /api/v1/research/tasks/{task_id}/events
```

### 10.3 报告

```text
POST /api/v1/research/reports
POST /api/v1/research/reports/comprehensive
```

综合报告接口最终返回：

```text
symbol
as_of
module_version
summary
narrative
sections
```

后续增加：

```text
evidence_citations
review_status
```

### 10.4 市场 / 技术

```text
GET /api/v1/market/snapshots/{symbol}
GET /api/v1/market/snapshots/{symbol}/summary
GET /api/v1/market/bars/{symbol}
GET /api/v1/market/bars/{symbol}/indicators
GET /api/v1/market/bars/{symbol}/cycle
```

### 10.5 基本面 / 财务 / 估值

```text
POST /api/v1/fundamental/analysis
```

后续扩展：

```text
POST /api/v1/financial/analysis
POST /api/v1/valuation/analysis
```

### 10.6 供应链

```text
GET /api/v1/supply-chain/graph
```

后续扩展：

```text
GET /api/v1/supply-chain/{symbol}
GET /api/v1/supply-chain/{symbol}/risk
```

### 10.7 审核

```text
GET  /api/v1/reviews/queue
POST /api/v1/reviews/{review_id}/decision
```

### 10.8 文档 / 引用

```text
POST /api/v1/files
GET  /api/v1/citations/documents/{document_id}/evidence
GET  /api/v1/citations/evidence/{evidence_id}
```

---

## 11. 数据库与模型边界

### 11.1 PostgreSQL

真相源：

```text
用户 / 权限
任务 / 版本 / 事件
行情 / K 线 / 新闻
财务事实
文档 / 证据 / Claim
合同 / 订单
审核 / 审计
Outbox
Feature Flag
```

### 11.2 Redis

缓存：

```text
热点行情摘要
临时状态
分布式锁
```

### 11.3 Neo4j

图投影：

```text
供应链节点
供应链关系
风险传播
```

### 11.4 Milvus

向量投影：

```text
文档 Dense 向量
未来 Sparse 向量
```

### 11.5 MinIO

文件存储：

```text
原始文档
文档版本
```

---

## 12. 异步与任务状态

任务状态：

```text
queued
running
completed
review_required
failed
rejected
```

异步执行：

```text
研究任务后台执行
Inbox 消费循环
Outbox 派发循环
文档解析和索引
Embedding
模型调用
LSTM 训练 / 预测
```

前端通过 SSE 接收：

```text
task.started
modules.started
agent.completed
review.completed
policy.decision
task.completed
task.failed
```

---

## 13. 综合报告和审核

### 13.1 报告生成

```text
各分析模块输出
    ↓
风险汇总
    ↓
结构化报告组装
    ↓
可选 Agent 生成中文叙述
    ↓
证据引用
    ↓
规则审核
    ↓
人工审核
```

### 13.2 审核状态

```text
REVIEW_REQUIRED
UNDER_REVIEW
APPROVED
NEEDS_REVISION
REJECTED
```

### 13.3 证据引用

关键结论必须包含：

```text
来源文档
来源类型
段落 / 页码
证据 ID
时间点
```

---

## 14. 部署方案

开发环境：

```text
docker compose up -d
```

服务：

```text
backend
web
postgres
redis
minio
etcd
minio-milvus
milvus
neo4j
prometheus
grafana
```

生产环境：

```text
docker-compose.prod.yml
必须注入生产密钥
必须启用 Refresh Cookie Secure
必须使用随机 JWT_SECRET_KEY
必须使用随机 COLLECTOR_INGEST_TOKEN
```

---

## 15. 开发阶段

### 阶段 1：主链路

```text
工作台页面
异步研究任务
综合报告接口
各分析模块结果展示
任务历史
审核中心
```

### 阶段 2：分析增强

```text
专业财务分析
估值分析
技术面趋势 / 周期结论
风险汇聚
供应链风险
```

### 阶段 3：RAG 增强

```text
标准 RAG 接入报告引用
Graph RAG
Agentic RAG
```

### 阶段 4：生产化

```text
安全加固
性能优化
完整监控
生产部署
灰度发布
```

---

## 16. 验收标准

### 16.1 功能验收

```text
输入股票代码可完成全部分析
各维度结果可在工作台查看
可生成综合报告
报告包含证据引用
报告包含人工审核状态
任务历史可查看
审核中心可处理待审核报告
```

### 16.2 技术验收

```text
后端单测通过
采集器单测通过
Ruff 通过
mypy 通过
前端 typecheck 通过
前端 lint 通过
前端 test 通过
OpenAPI / TS 契约一致
Neo4j 集成通过
Milvus 集成通过
Embedding 验证通过
```

### 16.3 安全验收

```text
越权访问被拒绝
未授权文档不可检索
Skill 默认拒绝
模型调用经过 Model Gateway
正式副作用经过 Outbox
结构化数字不被 RAG 猜测
```

---

## 17. 现有实现对照

当前已有：

```text
FastAPI 骨架
JWT / RBAC / ABAC
Workflow Event Store
Outbox
XTQuant Collector
Market / Technical Engine
Fundamental / Risk Engine
文档解析和标准 RAG
Neo4j 供应链图
多 Agent / LangGraph
Model Gateway
Skill Gateway
Human Review
前端骨架
```

需要补齐：

```text
统一的综合报告产品页面
基本面定性分析
专业财务分析增强
估值增强
风险汇聚
Graph RAG
Agentic RAG
证据引用在报告中的完整展示
审核状态在报告中的完整展示
```

---

## 18. 结论

本方案确定：

```text
产品形态：股票分析工作台 + 任务历史 + 审核中心
技术架构：LangGraph 混合编排
分析方式：确定性 Engine 为主，Agent 为辅
数据链路：XTQuant 采集，PostgreSQL 真相源，Neo4j / Milvus 投影
报告链路：多维度分析 → 风险汇聚 → 综合报告 → 证据引用 → 人工审核
检索链路：先标准 RAG，再补 Graph RAG 和 Agentic RAG
```
