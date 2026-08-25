# ADR-0002：上下文记忆使用 Redis 热缓存 + PostgreSQL Checkpoint

- 状态：Accepted
- 日期：2026-08-25
- 决策者：/root
- 影响阶段：P0 已有 checkpoint_ref 基座，P5 LangGraph 实施

## 背景

研究型 Agent 的上下文容易退化成两种反模式：

1. 把历史结论、证据、中间推理全部塞进模型上下文，导致不可审计、不可复现。
2. 把短期运行状态只放 Redis，导致 Redis 清空后无法恢复。

## 决策

- 长期业务记忆仍以 PostgreSQL `research_snapshot` 系列表为真相源。
- LangGraph 单次运行状态使用 Redis 作为热缓存，加速读、共享、恢复。
- 每个关键节点完成后，把 Checkpoint 同步写入 PostgreSQL `checkpoint_ref`。
- Redis 仅作为可重建的加速层，不作为唯一真相源。
- 禁止把模型私有思考过程写入 Redis 或 PostgreSQL。

## 约束

- Redis 清空后，系统必须能从 `checkpoint_ref` 重建运行状态。
- `checkpoint_ref.state` 只保存结构化状态字段，不保存 CoT。
- 缓存键必须包含 `tenant_id + task_id + checkpoint_id`，避免跨租户串用。
- 写 PostgreSQL 成功后才允许覆盖 Redis，避免缓存领先真相。

## 后果

P5 LangGraph 实施时，Checkpoint 持久化必须同时满足：

- Redis 快速读取
- PostgreSQL 持久真相
- 失败回源重建
- HITL 断点恢复
