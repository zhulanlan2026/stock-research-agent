# ADR-0003：多 Agent 运行时采用 LangGraph + 受控 ReAct

- 状态：Accepted
- 日期：2026-09-09
- 决策者：/root
- 影响阶段：P5 Multi-Agent / HITL 升级

## 背景

当前 `agents/` 下已经存在 `DocumentAgent`、`ResearchAgent`、`ReportAgent`、
`ReviewAgent`，但它们是确定性业务封装，未形成真正的多 Agent 运行时。
现有 `LinearResearchGraph` 只是顺序 fallback，不能表达并行、依赖、重试和 HITL。

投研业务需要多路独立分析并行执行，再做风险汇总、研究综合、报告、审核和发布。

## 决策

1. 采用 LangGraph 作为任务编排运行时。
2. LangGraph 不可用时，保留当前的确定性 `LinearResearchGraph` 作为 fallback，
   但 fallback 只允许执行确定性引擎，不允许生成正式模型结论。
3. 模型驱动 Agent 使用受控 ReAct 范式：

```text
Thought -> Action -> Observation -> ... -> Final Answer
```

4. ReAct 的 Action 只能通过 `SkillGateway` 调用，且每个 Agent 有
   `AgentManifest.allowed_skills` 白名单。
5. 确定性 Engine 不进入 ReAct 循环，只作为无模型副作用或只读 Skill 被调用。
6. 最终发布仍由 `Policy Engine + Outbox + HITL` 控制，Review Agent 不直接发布。

## 目标图结构

```text
START
 -> Intent Router
 -> Stock Identity
 -> Entitlement / Policy 预检查
 -> Parallel:
      Fundamental Agent
      Financial Agent
      Technical Agent
      Market Agent
      Supply Chain Agent
      News / Event Agent
      Evidence / Retrieval Agent
 -> Risk Agent
 -> Research Agent
 -> Report Agent
 -> Review Agent
 -> Policy Engine
      ALLOW  -> Outbox
      REVIEW -> HITL
      DENY   -> STOP
 -> DONE
```

当前实现进度：

- 统一 `AgentManifest` / `AgentContext` / `AgentResult` / `Agent` Protocol。
- `AgentRegistry` 提供依赖拓扑排序和分层执行计划。
- `AgentOrchestrator` 优先使用 LangGraph，未安装时回退 `ParallelAgentExecutor`。
- 受控 ReAct 循环、Skill 白名单、Token/Iteration 预算、审计记录已接入。
- `POST /api/v1/research/tasks` 已触发多 Agent DAG，并写入任务事件和版本。

## Agent 协议

- `AgentManifest`：名称、版本、执行类型、权限范围、允许 Skill、依赖关系。
- `AgentContext`：任务、租户、用户、标的、分析时点、模式、目的、当前 State。
- `AgentResult`：Agent 名、状态、结构化数据、警告、模块版本、耗时。
- `Agent` Protocol：`manifest` 和 `run(context)`。

## 约束

- Agent 不直接执行 SQL、不绕过 Risk、不扩大 TopK、不修改授权。
- 模型调用必须走 `ModelGateway`。
- 正式副作用必须走 `Policy + Outbox`。
- ReAct 循环有最大步数和超时，失败后降级或转 HITL。
- Agent 结果必须携带数据版本和模块版本，保持可复现。

## 后果

- `agents/` 下逐步增加协议、Registry、Orchestrator、LangGraph adapter、ReAct runtime。
- 现有线性 fallback 保留，但逐步收敛为降级路径。
- 后续每个 Agent 都必须先注册 manifest，再进入图执行。
