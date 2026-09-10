from __future__ import annotations

import builtins
import math
from collections.abc import Sequence
from typing import Any

from stock_research.market.cycle import CycleAnalysisService, LstmForecast
from stock_research.market.torch_lstm import TorchLstmCyclePredictor


def test_cycle_analysis_requires_minimum_samples() -> None:
    result = CycleAnalysisService().analyze([1.0, 2.0, 3.0])

    assert result.sample_count == 3
    assert result.fft_periods == ()
    assert result.wavelet_energy == ()
    assert result.lstm_available is False


def test_cycle_analysis_finds_fft_period_and_haar_energy() -> None:
    closes = [
        math.sin(2 * math.pi * index / 10)
        for index in range(80)
    ]

    result = CycleAnalysisService().analyze(closes)

    assert result.sample_count == 80
    assert result.fft_periods
    assert 9.5 <= result.fft_periods[0]["period_bars"] <= 10.5
    assert result.wavelet_energy
    assert result.lstm_available is False
    assert result.lstm_predictions == ()


def test_cycle_analysis_ignores_missing_close_values() -> None:
    closes: list[float | None] = [
        None if index == 0 else math.sin(2 * math.pi * index / 10)
        for index in range(81)
    ]

    result = CycleAnalysisService().analyze(closes)

    assert result.sample_count == 80


def test_cycle_analysis_uses_injected_lstm_predictor() -> None:
    class _FakePredictor:
        def predict(
            self,
            values: Sequence[float],
            *,
            horizon: int,
        ) -> LstmForecast:
            assert values
            assert horizon == 3
            return LstmForecast(
                available=True,
                predictions=(1.0, 2.0, 3.0),
            )

    service = CycleAnalysisService(lstm_predictor=_FakePredictor())
    result = service.analyze(
        [float(index) for index in range(40)],
        horizon=3,
    )

    assert result.lstm_available is True
    assert result.lstm_predictions == (1.0, 2.0, 3.0)


def test_torch_lstm_returns_unavailable_when_torch_is_missing(
    monkeypatch: Any,
) -> None:
    original_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "torch":
            raise ImportError("torch is not available")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    forecast = TorchLstmCyclePredictor().predict(
        [float(index) for index in range(40)],
        horizon=3,
    )

    assert forecast.available is False
    assert forecast.predictions == ()
    assert "torch is not installed" in (forecast.reason or "")
