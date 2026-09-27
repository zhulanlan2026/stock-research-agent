# akshare-collector

行情采集器，支持 AKShare 与 Tushare 两种行情主数据源，替换原 XTQuant/MiniQMT 采集器。
默认使用 AKShare 采集实时快照、公告、K 线，并用 Tushare 对日线做交叉验证；也可以切换为
Tushare 作为 K 线主数据源（支持日线/复权/分钟线）。

采集数据统一标准化后，推送到后端已有的 Ingest API：

```text
AKShare / Tushare
    ↓
SQLite WAL 本地缓冲
    ↓
POST /api/v1/ingest/events
    ↓
inbox_event -> PostgreSQL
```

输出事件类型：

- `market.bar`：历史 K 线
- `market.quote`：实时快照
- `market.announcement`：公告
- `financial.fact`：财务事实（本地 JSON Lines 或 Tushare 财务/估值指标）

## 运行

```bash
cd apps/akshare-collector
uv sync
uv run python -m akshare_collector.main
```

或在已有 Python 环境安装后运行：

```bash
pip install -e .
python -m akshare_collector.main
```

## 配置

复制 `.env.example` 为 `.env`，按需修改：

- `COLLECTOR_COLLECT_SYMBOLS`：A 股代码，逗号分隔。
- `COLLECTOR_COLLECT_PERIODS`：K 线周期。
- `COLLECTOR_MARKET_SOURCE`：`akshare`（默认）或 `tushare`。选 `tushare` 时只采集历史 K 线，
  实时快照与公告不可用。
- `COLLECTOR_TUSHARE_ADJUST`：Tushare 日线复权类型，空/`qfq`/`hfq`。
- `COLLECTOR_TUSHARE_TOKEN`：Tushare token；`market_source=tushare` 时必填，AKShare 交叉验证时留空则跳过。
- `COLLECTOR_FINANCIAL_SOURCE`：`jsonl`（默认）或 `tushare`。选 `tushare` 时用 Tushare
  `fina_indicator`、`daily_basic` 以及利润表/资产负债表/现金流量表生成财务/估值事实，
  需要 `COLLECTOR_TUSHARE_TOKEN`。
- `COLLECTOR_INGEST_TOKEN`：必须与后端一致。
