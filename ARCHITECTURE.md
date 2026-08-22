# Architecture

架构基线见 V2.0 技术方案，本文档只作入口说明。

核心边界：

- Vue 3 仅调用 `/api/v1/**`。
- PostgreSQL 是业务与状态唯一真相源。
- 正式数字和正式状态由确定性 Engine 产生。
- 数据先授权，再检索。
- Skill 默认拒绝。
- 正式副作用统一走 Policy + Outbox。
