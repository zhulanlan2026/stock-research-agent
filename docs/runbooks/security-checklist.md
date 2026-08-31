# Security Checklist

- 生产密钥通过 Secret Manager 注入，不进入仓库。
- `COLLECTOR_INGEST_TOKEN`、`JWT_SECRET_KEY` 生产环境随机且长度 >= 32。
- `REFRESH_COOKIE_SECURE=true`。
- DB/Redis/MinIO/Milvus/Neo4j 不公网暴露。
- Frontend 无 DeepSeek / DB / XTQuant / MinIO 密钥。
- 私有文档默认不进入外部模型。
- ACL 先于检索。
- Skill Gateway 默认拒绝。
- 正式副作用只走 Outbox。
- 依赖扫描、Secret 扫描纳入 CI。
