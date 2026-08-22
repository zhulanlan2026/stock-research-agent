# AGENTS.md

本仓库的开发以《MiniQMT_智能研股系统_V2.0_最终技术方案_Codex开发执行版.md》为唯一技术基线。

Agent 执行规则：

- 一次只执行一个明确的任务 ID 或小批次。
- 不改变前后端分离、PostgreSQL 真相源、OpenAPI 真相源、Engine 正式数字、Data Trust、
  ACL-before-retrieval、Skill Gateway、Policy + Outbox、HITL、P0-P6 阶段边界。
- 新增 Schema 同步 ORM / Pydantic / Migration / Test。
- 新增 API 同步 OpenAPI / Auth / Error / request_id / Test。
- 模型调用必须走 Model Gateway；正式副作用必须走 Outbox。
- 完成后运行相关 lint / typecheck / tests，并按 V2.0 第 50 节模板汇报。
