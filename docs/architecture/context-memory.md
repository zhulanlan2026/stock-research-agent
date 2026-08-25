# 上下文记忆管理执行级设计

> 本文件是对 V2.0 技术方案第 15.5、20、31 节的补充。
> 若与 V2.0 冲突，以 V2.0 为准。

## 1. 分层

| 层 | 存储 | 生命周期 | 用途 |
|---|---|---|---|
| 运行态 | LangGraph State | 单次任务 | 当前 Agent 工作状态 |
| 热缓存态 | Redis | 单次任务 / TTL | 加速运行态读写 |
| 断点态 | PostgreSQL `checkpoint_ref` | 任务周期 | 断点恢复、HITL |
| 长期态 | PostgreSQL `research_snapshot` 系列 | 长期 | 上次结论、历史变化、继续追问 |
| 审计态 | PostgreSQL `workflow_event` | 长期追加 | 重放、审计、SSE |
| UI 态 | Pinia / Local | 页面周期 | 用户交互，非业务记忆 |

## 2. 读写顺序

### 读取

```text
Redis hit -> 返回
Redis miss -> PostgreSQL checkpoint_ref -> 重建到 Redis -> 返回
PostgreSQL miss -> 从任务初始状态开始
```

### 写入

```text
1. 计算当前阶段 Checkpoint
2. 写入 PostgreSQL checkpoint_ref
3. 成功后写入 Redis（TTL）
```

禁止先写 Redis 再异步落 PostgreSQL。

## 3. 缓存键

```text
research:checkpoint:{tenant_id}:{task_id}:{checkpoint_id}
```

字段必须包含租户和任务边界，避免跨租户、跨任务复用。

## 4. 允许持久化的 Checkpoint 状态

仅结构化字段：

- `intent_resolved`
- `modules_completed`
- `evidence_ready`
- `decision_ready`
- `report_drafted`
- `review_completed`
- `hitl_waiting`
- `publication_pending`

明确禁止：

- 模型中间推理文本
- 未经授权的原始私有文档内容
- 临时 prompt 片段
- 未脱敏密钥

## 5. Redis 失效与恢复

- Redis 缓存默认 TTL，任务结束后可主动删除。
- Redis 清空后，PostgreSQL `checkpoint_ref` 必须足以恢复。
- HITL 等待期间不清除 `checkpoint_ref`。
- 同一任务重复写入使用 checkpoint_id 幂等。

## 6. 与现有模型的关系

现有 `checkpoint_ref`：

```text
task_id
checkpoint_id
node_id
state
```

P5 实施时新增：

- `ContextMemoryCache`：Redis 读写封装
- `CheckpointStore`：PostgreSQL 真相源封装
- 两个实现共享同一个结构化 State DTO

## 7. 验收

- Redis 清空后可恢复
- 跨租户缓存命中为 0
- 私有思考过程零持久化
- HITL 等待后可继续
- 相同输入 + 版本 = 相同 Checkpoint
