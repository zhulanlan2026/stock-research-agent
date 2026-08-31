# Milvus Rebuild Runbook

## 重建前

- 确认 PostgreSQL 中 Document / Evidence 状态完整。
- 停止检索写入。
- 记录当前 Milvus Collection 配置。

## 重建

```bash
# 删除旧 Collection
python - <<'PY'
from pymilvus import connections, utility
connections.connect(host="localhost", port="19530")
utility.drop_collection("evidence")
PY
```

## 重放

从 PostgreSQL 读取 `document_version` 和 `normalized_block`，重新生成 Dense / Sparse 向量并写入新 Collection。

## 验证

- `utility.has_collection("evidence")` 为 True。
- 查询测试返回结果。
- 运行 Golden Dataset 评估，Recall@K 达到阈值。
