# ADR-0004：技术面周期分析采用 FFT + Haar 小波 + 可选 LSTM

- 状态：Accepted
- 日期：2026-09-10
- 决策者：/root
- 影响阶段：P5 技术面 Agent / 行情可视化

## 背景

技术 Agent 最初只提供 MA、EMA、MACD、RSI 等经典指标，无法表达价格序列的
周期性、多尺度波动和模型预测需求。用户希望在同花顺式技术指标之外，增加：

- 傅里叶变换周期识别
- 小波变换多尺度能量分解
- LSTM 周期预测

这些分析需要明确区分“确定性数学结果”和“模型预测结果”，避免把统计预测
混入正式事实数字。

## 决策

1. FFT 和小波分析作为确定性计算进入 `TechnicalEngine`。
2. FFT 使用 `numpy.fft.rfft`，先做一阶线性去趋势，再输出主导周期及能量。
3. 小波使用纯 NumPy 实现的 Haar DWT，输出各层 detail 能量占比。
4. LSTM 作为可选模型运行时：
   - 默认关闭。
   - 未配置 torch 或样本不足时返回 `lstm_available=false`，不伪造预测。
   - 显式配置后通过 `TorchLstmCyclePredictor` 生成预测，结果必须标记为模型预测。
5. 技术 Engine 版本升级为 `technical:1.1.0`。
6. 新增 `GET /api/v1/market/bars/{symbol}/cycle`，把周期分析作为独立 API 输出。
7. 周期分析同时进入研究汇总、结构化报告和前端行情页。

## 数据契约

```text
CycleAnalysisResult
  - module_version
  - sample_count
  - fft_periods: [{period_bars, power}]
  - wavelet_energy: [{level, energy}]
  - lstm_available
  - lstm_reason
  - lstm_predictions: [number]
```

## 约束

- FFT/小波只依赖确定性收盘价序列，不调用外部模型。
- LSTM 输出不得作为审核决策或正式发布数字的唯一依据。
- 样本不足时必须返回空结果，禁止用插值或随机数补足。
- `lstm_available=false` 时必须给出原因，便于审计和前端展示。

## 后果

- `TechnicalEngine`、`TechnicalEngineAgent`、`ResearchSummaryAgent` 和
  `StructuredReportAgent` 已携带周期分析结果。
- 前端 `MarketView` 展示 FFT、小波和 LSTM 图表。
- 生产环境若需启用 LSTM，必须在镜像构建时设置 `INSTALL_TORCH=true`，并在运行时
  设置 `TECHNICAL_LSTM_ENABLED=true`。
