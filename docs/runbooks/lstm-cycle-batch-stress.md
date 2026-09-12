# LSTM 周期预测批量压测 Runbook

## 目标

验证启用 PyTorch LSTM 后，多个标的并发请求周期分析 API 的可用性、耗时和稳定性。

## 前置条件

- Docker 基础服务已启动：`postgres`、`redis`、`minio`
- backend 镜像包含 CPU 版 PyTorch：

```bash
INSTALL_TORCH=true docker compose build backend
```

- backend 环境已启用 LSTM：

```env
TECHNICAL_LSTM_ENABLED=true
TECHNICAL_LSTM_HIDDEN_SIZE=12
TECHNICAL_LSTM_EPOCHS=30
TECHNICAL_LSTM_WINDOW=12
```

## 准备测试数据

默认数据库只有 `600519.SH` 的日线数据。可用下面的 Python 脚本把同一批 K 线复制给其他标的：

```python
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from stock_research.stores.models.market import MarketBar

SOURCE = "600519.SH"
TARGETS = ["000001.SZ", "000858.SZ"]

async def main():
    engine = create_async_engine(
        "postgresql+asyncpg://research:research123@localhost:5432/research_db"
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        rows = (
            await session.execute(
                select(MarketBar).where(
                    MarketBar.symbol == SOURCE,
                    MarketBar.period == "1d",
                )
            )
        ).scalars().all()
        for symbol in TARGETS:
            session.add_all(
                [
                    MarketBar(
                        symbol=symbol,
                        period="1d",
                        bar_time=row.bar_time,
                        open=row.open,
                        high=row.high,
                        low=row.low,
                        close=row.close,
                        volume=row.volume,
                        amount=row.amount,
                        source_event_id=f"stress-{symbol}-{index}",
                    )
                    for index, row in enumerate(rows)
                ]
            )
        await session.commit()
    await engine.dispose()

asyncio.run(main())
```

## 执行压测

```bash
UV_OFFLINE=1 uv run python scripts/lstm_batch_stress.py \
  --symbols 600519.SH,000001.SZ,000858.SZ \
  --rounds 2 \
  --concurrency 3
```

可选参数：

- `--rounds`：每个标的重复次数
- `--concurrency`：并发请求数
- `--limit`：收盘价样本数
- `--period`：K 线周期，默认 `1d`

## 参考结果

当前超参数 `hidden=12 / epochs=30 / window=12` 下，三个标的各两轮：

| 标的 | 请求数 | 平均 HTTP 耗时 | 平均 LSTM 耗时 | LSTM 可用 |
|---|---:|---:|---:|---:|
| 000858.SZ | 2 | 12382.5ms | 4764.5ms | 2/2 |
| 600519.SH | 2 | 14745.5ms | 5060.5ms | 2/2 |
| 000001.SZ | 2 | 17107.0ms | 4881.0ms | 2/2 |

## 观察指标

压测后可从 backend `/metrics` 看到：

```text
technical_lstm_invocations_total
technical_lstm_latency_ms_last
```

Grafana 中的 `Stock Research LSTM Cycle` Dashboard 可查看：

- LSTM 推理耗时
- LSTM 调用次数

## 注意事项

- 当前 LSTM 每次请求都会重新训练，因此并发越高 CPU 占用越高。
- 若需降低延迟，优先减少 `TECHNICAL_LSTM_EPOCHS` 或 `TECHNICAL_LSTM_WINDOW`。
- 正式使用前应使用真实多标的数据集评估预测质量。
