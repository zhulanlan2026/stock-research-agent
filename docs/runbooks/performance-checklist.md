# Performance Checklist

- 关键 API P95 满足 SLO。
- Retrieval P95 达标：
  - Standard <= 1.5s
  - Major Risk <= 2.0s
- 数据库慢查询记录与索引检查。
- Redis 热快照命中率监控。
- Milvus 查询延迟监控。
- 前端大 Chunk 拆分 / 懒加载。
- 压测报告归档。
