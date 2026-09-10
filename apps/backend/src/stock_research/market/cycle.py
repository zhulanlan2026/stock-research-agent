from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

CYCLE_ANALYSIS_VERSION = "cycle:1.0.0"


@dataclass(frozen=True)
class LstmForecast:
    available: bool
    predictions: tuple[float, ...]
    reason: str | None = None
    latency_ms: int | None = None


class LstmCyclePredictor(Protocol):
    def predict(
        self,
        values: Sequence[float],
        *,
        horizon: int,
    ) -> LstmForecast:
        ...


@dataclass(frozen=True)
class CycleAnalysisResult:
    module_version: str
    sample_count: int
    fft_periods: tuple[dict[str, Any], ...]
    wavelet_energy: tuple[dict[str, Any], ...]
    lstm_available: bool
    lstm_reason: str | None
    lstm_predictions: tuple[float, ...]
    lstm_latency_ms: int | None


class CycleAnalysisService:
    """对收盘价序列做 FFT 周期识别与 Haar 小波能量分解。

    这是确定性数学计算，不调用 LLM。LSTM 属于可选模型运行时，当前未配置时
    明确返回 `lstm_available=False`，不会伪造预测值。
    """

    module_version = CYCLE_ANALYSIS_VERSION

    def __init__(
        self,
        *,
        lstm_predictor: LstmCyclePredictor | None = None,
    ) -> None:
        self._lstm_predictor = lstm_predictor

    def analyze(
        self,
        closes: Sequence[float | None],
        *,
        horizon: int = 5,
    ) -> CycleAnalysisResult:
        clean = np.asarray(
            [
                float(value)
                for value in closes
                if value is not None and math.isfinite(float(value))
            ],
            dtype=float,
        )
        if clean.size < 8:
            return CycleAnalysisResult(
                module_version=self.module_version,
                sample_count=int(clean.size),
                fft_periods=(),
                wavelet_energy=(),
                lstm_available=False,
                lstm_reason="insufficient sample size for cycle analysis",
                lstm_predictions=(),
                lstm_latency_ms=None,
            )

        fft_periods = _dominant_fft_periods(clean)
        wavelet_energy = _haar_energy_levels(clean)
        lstm_forecast = self._forecast(clean, horizon)
        return CycleAnalysisResult(
            module_version=self.module_version,
            sample_count=int(clean.size),
            fft_periods=fft_periods,
            wavelet_energy=wavelet_energy,
            lstm_available=lstm_forecast.available,
            lstm_reason=lstm_forecast.reason,
            lstm_predictions=lstm_forecast.predictions,
            lstm_latency_ms=lstm_forecast.latency_ms,
        )

    def _forecast(
        self,
        values: np.ndarray[Any, np.dtype[np.floating[Any]]],
        horizon: int,
    ) -> LstmForecast:
        if self._lstm_predictor is None:
            return LstmForecast(
                available=False,
                predictions=(),
                reason=(
                    "LSTM runtime is not configured; connect an optional "
                    "torch/model adapter before enabling LSTM forecasts"
                ),
                latency_ms=None,
            )
        return self._lstm_predictor.predict(
            [float(value) for value in values],
            horizon=horizon,
        )


def _dominant_fft_periods(
    values: np.ndarray[Any, np.dtype[np.floating[Any]]],
) -> tuple[dict[str, Any], ...]:
    x_axis = np.arange(values.size, dtype=float)
    trend = np.polyval(np.polyfit(x_axis, values, 1), x_axis)
    residual = values - trend
    spectrum = np.abs(np.fft.rfft(residual)) ** 2
    frequencies = np.fft.rfftfreq(values.size, d=1.0)

    candidates: list[tuple[float, float]] = []
    for index in range(1, frequencies.size):
        frequency = float(frequencies[index])
        if frequency <= 0:
            continue
        period = 1.0 / frequency
        if period < 2 or period > values.size:
            continue
        candidates.append((float(spectrum[index]), period))

    candidates.sort(key=lambda item: item[0], reverse=True)
    return tuple(
        {
            "period_bars": round(period, 4),
            "power": round(power, 8),
        }
        for power, period in candidates[:5]
    )


def _haar_energy_levels(
    values: np.ndarray[Any, np.dtype[np.floating[Any]]],
) -> tuple[dict[str, Any], ...]:
    total_energy = float(np.sum(values**2))
    if total_energy <= 0:
        return ()

    coefficients = values
    energy: list[dict[str, Any]] = []
    level = 1
    while coefficients.size >= 2:
        usable = coefficients.size - (coefficients.size % 2)
        pairs_odd = coefficients[:usable:2]
        pairs_even = coefficients[1:usable:2]
        approximation = (pairs_odd + pairs_even) / math.sqrt(2.0)
        detail = (pairs_odd - pairs_even) / math.sqrt(2.0)
        detail_energy = float(np.sum(detail**2))
        energy.append(
            {
                "level": level,
                "energy": round(detail_energy / total_energy, 8),
            }
        )
        coefficients = approximation
        level += 1
    return tuple(energy)
