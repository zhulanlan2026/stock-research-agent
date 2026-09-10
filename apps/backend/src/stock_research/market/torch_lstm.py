from __future__ import annotations

import math
import time
from collections.abc import Sequence
from typing import Any

import structlog

from stock_research.market.cycle import LstmForecast
from stock_research.observability.metrics import get_prometheus_registry

logger = structlog.get_logger(__name__)


class TorchLstmCyclePredictor:
    """可选 PyTorch LSTM 周期预测适配器。

    仅在调用方显式注入后运行。训练使用固定随机种子和归一化输入，输出必须
    作为模型预测而非确定性事实处理。
    """

    def __init__(
        self,
        *,
        seed: int = 0,
        hidden_size: int = 8,
        epochs: int = 50,
        window: int = 20,
    ) -> None:
        self._seed = seed
        self._hidden_size = hidden_size
        self._epochs = epochs
        self._window = window

    def predict(
        self,
        values: Sequence[float],
        *,
        horizon: int,
    ) -> LstmForecast:
        clean = [
            float(value)
            for value in values
            if math.isfinite(float(value))
        ]
        try:
            import torch  # type: ignore[import-not-found]
        except ImportError as exc:
            return LstmForecast(
                available=False,
                predictions=(),
                reason=f"torch is not installed: {exc}",
            )

        window = min(self._window, max(4, len(clean) // 2))
        if len(clean) < window + 1:
            return LstmForecast(
                available=False,
                predictions=(),
                reason="insufficient sample size for LSTM training",
            )

        torch.manual_seed(self._seed)
        series = torch.tensor(clean, dtype=torch.float32)
        mean = float(series.mean())
        std = float(series.std())
        if std <= 0:
            return LstmForecast(
                available=False,
                predictions=(),
                reason="close prices have zero variance",
            )
        started = time.perf_counter()
        normalized = (series - mean) / std

        inputs = [
            normalized[index : index + window]
            for index in range(len(normalized) - window)
        ]
        targets = [
            normalized[index + window]
            for index in range(len(normalized) - window)
        ]
        x_tensor = torch.stack(inputs).unsqueeze(-1)
        y_tensor = torch.stack(targets)

        class _LstmModule(torch.nn.Module):  # type: ignore[misc]
            def __init__(
                self,
                *,
                input_size: int,
                hidden_size: int,
            ) -> None:
                super().__init__()
                self.lstm = torch.nn.LSTM(
                    input_size=input_size,
                    hidden_size=hidden_size,
                    batch_first=True,
                )
                self.head = torch.nn.Linear(
                    hidden_size,
                    1,
                )

            def forward(self, inputs: Any) -> Any:
                output, _ = self.lstm(inputs)
                return self.head(output[:, -1, :])

        model = _LstmModule(
            input_size=1,
            hidden_size=self._hidden_size,
        )
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        loss_fn = torch.nn.MSELoss()

        for _ in range(self._epochs):
            optimizer.zero_grad()
            predicted = model(x_tensor)
            loss = loss_fn(predicted.squeeze(-1), y_tensor)
            loss.backward()
            optimizer.step()

        model.eval()
        current = normalized[-window:].unsqueeze(0).unsqueeze(-1)
        predictions: list[float] = []
        with torch.no_grad():
            for _ in range(horizon):
                next_value = float(model(current).squeeze())
                predictions.append(round(next_value * std + mean, 6))
                next_tensor = torch.tensor(
                    [[[next_value]]],
                    dtype=torch.float32,
                )
                current = torch.cat(
                    (current[:, 1:, :], next_tensor),
                    dim=1,
                )

        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "lstm cycle prediction completed",
            sample_count=len(clean),
            horizon=horizon,
            latency_ms=latency_ms,
        )
        metrics = get_prometheus_registry()
        metrics.inc_counter("technical_lstm_invocations_total")
        metrics.set_gauge("technical_lstm_latency_ms_last", float(latency_ms))
        return LstmForecast(
            available=True,
            predictions=tuple(predictions),
            latency_ms=latency_ms,
        )
