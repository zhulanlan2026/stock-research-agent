# 真实 XTQuant / 财务 / 新闻数据接入 Runbook

## 目标

把 Windows MiniQMT/XTQuant 的真实行情、历史 K 线、公告，以及本地财务事实文件接入后端 PostgreSQL。

## 前置条件

- Windows 机器已安装并启动 MiniQMT。
- `xtquant` Python 包已在 Windows 环境可用。
- 后端基础设施已启动：

```bash
docker compose up -d
```

- collector 环境变量已配置：

```env
COLLECTOR_BACKEND_URL=http://<后端地址>/api/v1
COLLECTOR_INGEST_TOKEN=<后端 COLLECTOR_INGEST_TOKEN>
COLLECTOR_COLLECT_SYMBOLS=600519.SH,000001.SZ
COLLECTOR_COLLECT_PERIODS=1m,1d
COLLECTOR_COLLECT_NEWS_ENABLED=true
COLLECTOR_COLLECT_NEWS_KINDS=announcement
COLLECTOR_COLLECT_FINANCIAL_ENABLED=true
COLLECTOR_FINANCIAL_DATA_PATH=./data/financial-facts.jsonl
```

## 财务事实文件格式

默认路径：

```text
apps/xtquant-collector/data/financial-facts.jsonl
```

每行一条 JSON：

```json
{"symbol":"600519.SH","metric":"revenue","period":"2025Q4","value":"1200.00","unit":"CNY","source_id":"real-demo","disclosed_at":1767225600000,"available_at":1767225600000}
```

字段说明：

- `symbol`：股票代码
- `metric`：财务指标
- `period`：报告期，例如 `2025Q4`
- `value`：数值
- `unit`：单位，例如 `CNY` / `shares`
- `source_id`：来源 ID
- `disclosed_at` / `available_at`：毫秒时间戳

## 启动 collector

```bash
cd apps/xtquant-collector
uv run python -m xtquant_collector.main
```

collector 会：

```text
读取配置
  -> 初始化 SQLite WAL
  -> 拉取历史 K 线
  -> 拉取公告
  -> 读取财务事实文件
  -> 订阅实时行情
  -> 批量推送 Ingest API
```

## 后端核对

```bash
docker exec research-postgres psql -U research -d research_db -c "SELECT count(*) FROM inbox_event;"
docker exec research-postgres psql -U research -d research_db -c "SELECT count(*) FROM market_bar;"
docker exec research-postgres psql -U research -d research_db -c "SELECT count(*) FROM market_news;"
docker exec research-postgres psql -U research -d research_db -c "SELECT count(*) FROM financial_fact;"
```

预期：

- `inbox_event` 持续增加
- `market_bar` 有真实 K 线
- `market_news` 有公告
- `financial_fact` 有财务事实

## 常见问题

### Ingest 返回 401

检查后端和 collector 的 `COLLECTOR_INGEST_TOKEN` 是否一致。

### 公告为空

XTQuant 公告字段随版本变化，建议先用 announcement 类型，确认返回结构后再校正字段映射。

### 财务事实未入库

确认：

- `COLLECTOR_COLLECT_FINANCIAL_ENABLED=true`
- `COLLECTOR_FINANCIAL_DATA_PATH` 指向的文件存在
- 文件中的 `symbol` 与 `COLLECTOR_COLLECT_SYMBOLS` 匹配
