# stock-research-platform

个股智能研究平台。当前仓库按《MiniQMT_智能研股系统_V2.0_最终技术方案_Codex开发执行版.md》
作为唯一技术基线（Single Source of Truth）执行。

## 目录

- `apps/web`：Vue 3 + Vite + TypeScript 前端
- `apps/backend`：FastAPI + LangGraph 后端
- `apps/xtquant-collector`：Windows MiniQMT/XTQuant 采集器
- `packages/api-types`：OpenAPI 自动生成的 TypeScript SDK
- `packages/shared-contracts`：跨语言稳定契约（错误码、枚举、SSE Schema、Feature Flag）
- `infrastructure`：基础设施配置
- `tests`：跨模块测试
- `docs`：架构、ADR、API、Runbook

## 快速开始

```bash
make setup
make infra-up
make backend-dev
make web-dev
```

## 契约

REST 契约唯一链路：

```text
FastAPI / Pydantic -> OpenAPI -> packages/api-types -> Vue API layer
```

```bash
make contracts-check
```
