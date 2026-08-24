# ADR-0001：知识库 / 文档处理 / 检索执行级优化

- 状态：Accepted
- 日期：2026-08-24
- 决策者：/root
- 影响阶段：P3 Document / Evidence / Retrieval

## 背景

V2.0 技术方案第 14-16 节与 P3 任务清单定义了知识库的方向，但停留在流程级。
为了避免 P3 开发时反复返工，需要在不改变既有架构原则的前提下，补充执行级契约：

1. P3 核心数据对象与 PostgreSQL 真相源字段。
2. 文档处理状态机与幂等重处理。
3. Parser Router / NormalizedBlock 统一输出契约。
4. ACL-before-retrieval 的过滤表达式生成方式。
5. Milvus 双路索引与 Neo4j Evidence 绑定。
6. 检索质量门禁、Golden Dataset 与可观测性。
7. 文档删除 / 修订 / 密文抹除的传播语义。

## 决策

采用 [knowledge-base.md](../architecture/knowledge-base.md) 作为 P3 执行级补充基线。

## 不变约束

- PostgreSQL 仍是业务与状态唯一真相源。
- Milvus / Neo4j / MinIO 均可重建，重建后 PostgreSQL 可恢复正式业务状态。
- 精确数字只走 Structured，Structured 缺失时返回“无可靠结构化数据”，禁止从 RAG 猜数。
- 所有 Document / Chunk / Evidence / Claim / Graph Edge 在检索前完成 ACL 约束。
- 私有文档禁止公共向量化；`external_model_allowed=false` 禁止流向外部模型。

## 后果

- P3 开发必须按补充契约同步 ORM / Pydantic / Migration / Test。
- 后续若修改本 ADR，需重新评审并更新 AGENTS.md 与 CODEX_TASKS.md。
