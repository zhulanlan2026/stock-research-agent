# 知识库 / 文档处理 / 检索执行级设计

> 本文件是对 V2.0 技术方案第 14-16 节与 P3 任务清单的执行级补充。
> 若与 V2.0 冲突，以 V2.0 为准；本文件只做细化，不改变架构原则。

## 1. 目标与边界

知识库负责把原始文件变成：

- 可授权的 `Document` / `DocumentVersion`
- 可引用的 `Evidence`
- 可审核的 `Claim` / `RiskClaim`
- 可检索的 Dense / Sparse Chunk
- 可解释的 Graph Edge

知识库不负责：

- 产生正式财务 / 技术 / 评分数字
- 自动发布正式结论
- 未经 HITL 的正式副作用

## 2. 核心实体与真相源

PostgreSQL 保存以下业务事实：

| 实体 | 关键字段 | 说明 |
|---|---|---|
| source | source_id, source_level, visibility_scope, license_policy_id, external_model_allowed | 来源可信等级与授权边界 |
| document | document_id, source_id, tenant_id, owner_id, symbol, document_type, content_hash, status, available_at | 唯一键 `source_id + external_id + revision_no` |
| document_version | document_version_id, document_id, version_no, raw_object_key, parser, parser_version, status, parsed_at | 可重放解析 |
| normalized_block | block_id, document_version_id, page_start, page_end, section, content_hash, block_type | 解析后的确定性中间态 |
| evidence | evidence_id, root_evidence_id, document_id, page, section, content_hash, source_level, citation_ready | 根证据与引用片段分离 |
| claim | claim_id, subject, predicate, object, valid_from, valid_to, verification_status, confidence, evidence_ids | 候选事实，DRAFT 不视为正式 |
| risk_claim | risk_claim_id, claim_id, risk_type, direction, materiality, status | 风险线索 |
| authorization_policy | authorization_policy_id, policy_json, effective_from, effective_to | 检索前 ACL 的版本化策略 |

Milvus 是 Dense / Sparse 索引投影，Neo4j 是 Graph 关系投影，二者均可重建。

## 3. 文档处理状态机

```text
UPLOADED
 -> MALWARE_SCANNED
 -> RAW_STORED
 -> PARSING
 -> PARSED
 -> NORMALIZED
 -> CHUNKED
 -> CLAIM_DRAFTED
 -> ACL_ATTACHED
 -> INDEXED
 -> CITATION_READY
```

终态：

- `SUPERSEDED`：新版本接管
- `REDACTED`：授权撤销或密文抹除
- `REJECTED`：不支持格式或安全检查失败
- `FAILED`：处理失败，可重放

幂等要求：

- 同一 `document_version` 用确定性 `content_hash` 判断是否已处理。
- 重处理不产生重复 Chunk / Evidence。
- 删除文档后，Milvus / Neo4j / MinIO 的关联投影必须可追踪地清理或标记不可见。

## 4. Parser Router 契约

所有 Parser 统一输出 `NormalizedBlock`：

```json
{
  "block_id": "blk_xxx",
  "document_version_id": "dv_xxx",
  "page_start": 3,
  "page_end": 5,
  "section": "主要合同",
  "block_type": "table",
  "content_hash": "sha256:...",
  "text": "...",
  "table": {"columns": [], "rows": []},
  "bbox": []
}
```

规则：

- 禁止“所有 PDF 直接 extract_text() 后进入 RAG”。
- 表格必须保留结构化行 / 列，不得压平成无结构文本后当作数字来源。
- 解析失败要保留失败现场与重试计数。
- Parser 版本、依赖版本、模型版本写入 `document_version`。

## 5. ACL-before-retrieval

检索前从 IAM / Entitlement 生成过滤表达式，而不是检索后过滤：

```text
tenant_id == T
AND owner_id IN allowed_owner_set
AND visibility_scope IN allowed_visibility
AND license_policy_id IN allowed_license_set
AND symbol IN allowed_symbol_set
AND available_at <= now
```

约束：

- 默认 `DENY`，未命中显式授权不可见。
- Chunk / Evidence / Graph Edge 都复制同一授权快照。
- `external_model_allowed=false` 的内容仅进入内部检索，不进入外部模型上下文。
- 授权策略变化通过版本化 `authorization_policy` 记录，变更可审计。

## 6. 检索索引布局

Milvus Collection 同时保留：

- `chunk_id`
- `dense_vector`
- `sparse_vector`
- `document_id`
- `root_evidence_id`
- `source_level`
- `visibility_scope`
- `license_policy_id`
- `symbol`
- `available_at`
- `external_model_allowed`
- `content_hash`

检索硬约束：

- Dense 检索前先带 ACL filter。
- 同一文档最多 3 个 Chunk，同一 Root Evidence 最多 2 个 Chunk，同一研报最多 2 个 Chunk。
- RRF 后按 `root_evidence_id` 去重，保留引用质量更高的片段。

## 7. 检索模式预算

| 模式 | lexical | dense | rerank_input | final_evidence |
|---|---|---|---|---|
| quick | 12 | 12 | 16 | 12 |
| standard | 30 | 30 | 40 | 24 |
| deep | 60 | 60 | 80 | 48 |
| major_risk | 40 | 30 | 50 | 24 |

## 8. 质量门禁与 Golden Dataset

Golden Dataset 至少覆盖：

- 公开财报页码引用
- 授权研报引用
- 私有文档零泄漏
- 跨租户未授权召回
- 结构化数字与 RAG 文本数字冲突
- 版本修订后旧版本不可见
- 删除 / 密文抹除后不可召回

指标：

- `recall@k`
- `precision@k`
- `MRR`
- `citation_coverage`
- `answer_groundedness`
- `acl_leakage = 0`
- `rag_guessed_number = 0`

门禁：

- 私有 ACL 泄漏必须为 0。
- 结构化数字缺失时不得由 RAG 补齐。
- 检索质量低于阈值时阻止进入正式报告。

## 9. 可观测性与审计

每次检索记录：

- `request_id`
- `tenant_id`
- `user_id`
- 查询意图 / 子查询
- ACL filter
- 各路候选数
- RRF 前后排序
- 去重与重排结果
- 最终 Evidence Pack
- 模型 / 向量 / Reranker 版本
- 各阶段延迟

审计指标：

- retrieval empty
- retrieval latency
- retrieval candidate drop
- acl filter mismatch
- index freshness
- rebuild status

## 10. 重建 / 恢复

- Milvus Rebuild：从 PostgreSQL 的 Document / Evidence 状态重放并重新向量化。
- Neo4j Rebuild：从 Claim / Evidence 状态重建 Edge，并保留 Evidence 绑定、有效时间、审核状态。
- MinIO Versioning：原始文件版本不可变，修订创建新版本。
- 重建完成后运行 Golden Dataset 回归，验证 ACL 零泄漏。
