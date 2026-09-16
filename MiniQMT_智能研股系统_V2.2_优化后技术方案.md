# MiniQMT 智能研股系统 V2.2 优化后技术方案

> 文档状态：已确认并部分落地  
> 适用范围：股票研究系统前端 + 后端  
> 替代版本：`MiniQMT_智能研股系统_V2.1_前后端技术方案.md`  
> 目标：在 V2.1 基础上，记录已落地的架构优化、漏洞修复和下一阶段待办

---

## 1. 方案结论

本版本采用：

```text
LangGraph 混合编排
    + 确定性 Engine
    + 受控 Agent
    + 统一内部数据访问层
    + Model Gateway
    + Skill Gateway
    + Outbox
    + HITL
```

核心原则：

```text
能确定性计算的，用 Engine。
能写代码算清楚的，不交给 LLM。
非结构化理解、推理、表达，才用 Agent。
结构化数字缺失时，不得由 RAG 猜测。
正式副作用必须经过 Outbox。
```

---

## 2. 已落地优化

### 2.1 统一内部数据访问层

新增：

```text
apps/backend/src/stock_research/services/data_access.py
```

包含：

```text
MarketDataService
FinancialDataService
ValuationService
RiskService
SupplyChainDataService
DocumentRetrievalService
```

调用关系：

```text
Agent
    ↓
统一 Service
    ↓
PostgreSQL / Redis / Neo4j / Milvus
```

核心 Agent 已改为通过统一服务层访问数据。

### 2.2 as_of 时间一致性

已扩展到：

```text
MarketSnapshotStore
MarketBarStore
MarketBarService
IndicatorService
TechnicalEngine
MarketEngine
RiskEngine
MarketDataService
```

规则：

```text
用户选择 as_of
    ↓
所有模块统一使用 as_of
    ↓
财务、行情、K线、新闻、风险都按同一时间口径取数
```

### 2.3 部分失败降级

编排器已调整：

```text
某个 Agent 失败
    ↓
记录 FAILED
    ↓
其他 Agent 继续执行
    ↓
报告继续生成
```

不再因为 Neo4j、Milvus 或某个数据源异常导致整个任务失败。

### 2.4 模型失败确定性降级

保持：

```text
模型失败
    ↓
回退确定性汇总
    ↓
回退确定性报告
```

模型只负责：

```text
文档理解
关系抽取
新闻摘要
报告叙述
```

### 2.5 结构化数据优先

当前链路已保证：

```text
财务数字只来自 financial_fact
技术指标只来自 K 线 Engine
估值数字只来自 Valuation Engine
风险评分只来自 Risk Engine
RAG 只负责文档证据
```

### 2.6 Outbox 副作用

新增：

```text
review.decision
```

审核决策会写入 Outbox，并注册 handler：

```text
handle_review_decision
```

### 2.7 版本一致性

研究汇总现在携带：

```text
module_versions
```

综合报告新增：

```text
概览.as_of
概览.module_versions
版本信息章节
```

### 2.8 数据可用性

技术面和市场面摘要新增：

```text
data_available
```

### 2.9 报告权限

综合报告接口：

```text
POST /api/v1/research/reports/comprehensive
```

要求：

```text
report.read
```

### 2.10 免责声明

综合报告新增：

```text
免责声明章节
```

---

## 3. 总体技术架构

```text
前端 Vue 3 + Vite + ECharts
    ↓
FastAPI + JWT/RBAC/ABAC
    ↓
异步任务 + SSE
    ↓
LangGraph 编排
    ↓
统一数据访问层
    ↓
确定性 Engine + 受控 Agent
    ↓
Model Gateway / Skill Gateway
    ↓
PostgreSQL / Redis / Neo4j / Milvus / MinIO
    ↓
综合报告 + 证据引用 + 人工审核
```

---

## 4. 分析模块和实现方式

| 模块 | 实现方式 |
|---|---|
| 市场分析 | 确定性 Engine |
| 技术面分析 | 确定性 Engine + FFT / 小波 / LSTM |
| 基本面分析 | 受控 Agent + RAG |
| 财务分析 | 确定性 Engine |
| 估值分析 | 确定性 Engine |
| 供应链分析 | Neo4j + 确定性风险传播 |
| 风险分析 | 确定性聚合 Engine |
| 综合报告 | 工作流组装 + 可选 Agent 润色 |

---

## 5. LangGraph 范式

| 范式 | 使用位置 |
|---|---|
| DAG / Workflow | 市场、技术、财务、估值、风险、报告组装 |
| ReAct | 基本面、供应链抽取、新闻解读、报告叙述 |
| Plan-Execute | Deep 模式、多跳证据研究 |
| Reflection | 报告质量检查、基本面结论修订 |
| HITL | 人工审核 |

---

## 6. 关键漏洞修复状态

| 漏洞 | 状态 |
|---|---|
| as_of 时间一致性 | 已落地 |
| 部分失败降级 | 已落地 |
| 模型失败确定性降级 | 已落地 |
| 结构化数据优先 | 已落地 |
| Outbox 正式副作用 | 已落地 |
| 版本一致性 | 已落地 |
| 数据覆盖度 | 已落地 |
| 综合报告权限 | 已落地 |
| 免责声明 | 已落地 |
| 证据强度展示 | 已落地 |
| 估值增强 | 已落地 |
| LSTM 可复现性 | 已落地 |
| 供应链人工确认 | 已落地 |
| 前端 SSE 重连 / 取消 | 待补 |
| 可观测性 | 待补 |
| 备份 / 回滚 / 灰度 | 待补 |

---

## 7. 下一步开发顺序

### 阶段 1：数据完整

```text
补入 K 线数据
补入财务数据
补入供应链数据
补入新闻公告数据
```

### 阶段 2：分析增强

```text
专业财务分析
估值分析增强
风险因子细化
供应链风险
```

### 阶段 3：RAG 增强

```text
标准 RAG 接入报告引用
Graph RAG
Agentic RAG
```

### 阶段 4：前端产品化

```text
股票分析工作台
任务历史
审核中心
图表可视化
SSE 断线重连
```

### 阶段 5：生产化

```text
安全加固
监控告警
备份恢复
灰度发布
回滚方案
```

---

## 8. 当前验证结果

已通过：

```text
Ruff
mypy
test_engine_agents
test_report_pipeline
test_model_report_pipeline
test_risk_engine
```

综合报告接口已确认返回：

```text
概览
财务
技术
周期分析
行情
供应链
新闻
风险
版本信息
免责声明
```

---

## 9. 结论

当前版本已经完成：

```text
统一数据访问层
as_of 时间一致性
部分失败降级
模型降级
结构化数据优先
Outbox 副作用
版本记录
数据可用性标记
报告权限
免责声明
```

后续继续补齐：

```text
证据强度展示
估值增强
LSTM 复现
供应链人工确认
前端体验
生产化能力
```
