# P0 开发环境手动验收清单

> 用途：Codex 沙箱无法运行 Docker/PostgreSQL，以下步骤在你本机开发环境执行。
> 完成后即可补全 P0 Gate 的真实联调验证，再进入 P1。

## 1. 启动基础设施

```bash
cd ~/project/stock-research-agent
docker compose up -d
docker compose ps
```

确认 `research-postgres`、`research-redis`、`research-minio` 状态为 `healthy`。

## 2. 运行迁移闭环

```bash
cd ~/project/stock-research-agent
./venv/bin/uv run pytest apps/backend/tests/unit/test_migrations.py -s
```

预期：`1 passed`。

## 3. 启动后端 API

```bash
cd ~/project/stock-research-agent
./venv/bin/uv run uvicorn stock_research.main:app --host 0.0.0.0 --port 8000 --reload
```

检查：

```bash
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
```

`/health/ready` 在 PostgreSQL/Redis/MinIO 均可用时返回 200。

## 4. 准备种子用户

当前没有注册接口，需要手工插入一个开发用户：

```bash
cd ~/project/stock-research-agent
./venv/bin/uv run python - <<'PY'
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine("postgresql+asyncpg://research:research123@localhost:5432/research_db")
    async with engine.begin() as conn:
        # 这里先输出表结构，后续用正式 seed 脚本替代
        result = await conn.execute(text("select tablename from pg_tables where schemaname='public' order by tablename"))
        print([row[0] for row in result])
    await engine.dispose()

asyncio.run(main())
PY
```

> 建议后续新增 `scripts/seed_dev_user.py`，用 Argon2id 生成密码并写入 `tenant`、`user`、`credential`、`role`、`user_role`。

## 5. 启动前端

```bash
cd ~/project/stock-research-agent
pnpm --filter @stock-research/web dev
```

浏览器打开 `http://localhost:5173`，使用种子用户登录，验证：

- 登录成功进入工作台
- 401 后自动刷新
- 退出登录回到登录页

## 6. 联调研究任务

登录后获取 Access Token，然后：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/research/tasks \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"600519.SH","mode":"standard","modules":["fundamental","technical","market"]}'
```

再查询任务和 SSE：

```bash
curl http://127.0.0.1:8000/api/v1/research/tasks/<task_id>
curl -N http://127.0.0.1:8000/api/v1/research/tasks/<task_id>/events
```

## 7. 契约检查

```bash
cd ~/project/stock-research-agent
./venv/bin/uv run python scripts/export_openapi.py
pnpm --filter @stock-research/api-types generate
git diff --exit-code -- packages/shared-contracts/openapi/openapi.json packages/api-types/src
```

预期无差异。

## 8. 待补项

- [x] 全局异常处理（统一 `request_id + error{code,message,details}`，禁止 traceback）
- [x] `POST /research/tasks` 的 `Idempotency-Key`
- [x] `scripts/seed_dev_user.py`
- [x] CI 增加 `bandit`、`pip-audit`、`npm audit`
- [x] RBAC role_permission 存法决策：采用 `role_permission` 关联表，PostgreSQL 为真相源
- [x] Refresh Cookie 生产环境开启 `Secure`：`APP_ENV=production` 时强制校验
- [x] 生产环境注入 `JWT_SECRET_KEY`：`APP_ENV=production` 时强制校验

## 9. 已补齐的集成测试

以下测试在真实 PostgreSQL 环境可运行，沙箱中自动跳过：

```bash
./venv/bin/uv run pytest apps/backend/tests/api -s
```

- `test_auth.py`：登录成功、`/users/me`、错误密码
- `test_workflow.py`：research task 的 Idempotency-Key 幂等
- `test_admin_permission.py`：FREE_USER 访问 admin 接口被拒绝（权限负向测试）
- `test_auth.py::test_refresh_reuse_detection`：刷新令牌复用检测
