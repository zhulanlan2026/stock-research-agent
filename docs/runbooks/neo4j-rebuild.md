# Neo4j Rebuild Runbook

## 重建前

- 确认 PostgreSQL 中 Claim / Evidence 完整。
- 停止 Graph Publish。

## 清空图

```cypher
MATCH (n)
DETACH DELETE n;
```

## 重放

从审核通过的 Claim 和 Graph Candidate 重新发布节点与边，确保边绑定 Evidence。

## 验证

- 节点数量正确。
- 边包含 `evidence_ids`。
- 未绑定 Evidence 的边数量为 0。
