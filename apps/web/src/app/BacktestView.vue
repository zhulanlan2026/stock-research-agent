<script setup lang="ts">
import * as echarts from 'echarts';
import { nextTick, onBeforeUnmount, ref } from 'vue';

import { http } from '../api/client';

type Metrics = {
  bars: number;
  buy_hold_return: number;
  strategy_return: number;
  annualized_return: number;
  max_drawdown: number;
  trades: number;
};

type BacktestResponse = {
  symbol: string;
  strategy: string;
  short_window: number;
  long_window: number;
  metrics: Metrics;
  curve: Array<{ time: string; equity: number }>;
};

const form = ref({
  symbol: '603893.SH',
  short_window: 20,
  long_window: 60,
});
const loading = ref(false);
const error = ref('');
const result = ref<BacktestResponse | null>(null);
const chartRef = ref<HTMLDivElement | null>(null);
let chart: ReturnType<typeof echarts.init> | null = null;

function errorMessage(err: unknown, fallback: string): string {
  if (typeof err !== 'object' || err === null) {
    return fallback;
  }
  const response = (err as { response?: { data?: { detail?: { message?: string } } } }).response;
  return response?.data?.detail?.message || fallback;
}

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

async function runBacktest(): Promise<void> {
  loading.value = true;
  error.value = '';
  result.value = null;
  try {
    const { data } = await http.post<BacktestResponse>('/backtest', {
      symbol: form.value.symbol.trim(),
      short_window: form.value.short_window,
      long_window: form.value.long_window,
    });
    result.value = data;
    await nextTick(renderCurve);
  } catch (err: unknown) {
    error.value = errorMessage(err, '回测失败');
  } finally {
    loading.value = false;
  }
}

function renderCurve(): void {
  if (!chartRef.value || !result.value) {
    return;
  }
  chart?.dispose();
  chart = echarts.init(chartRef.value);
  chart.setOption({
    title: { text: '策略净值曲线' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'time' },
    yAxis: { type: 'value', scale: true },
    series: [
      {
        type: 'line',
        showSymbol: false,
        data: result.value.curve.map((point) => [point.time, point.equity]),
      },
    ],
  });
}

onBeforeUnmount(() => {
  chart?.dispose();
});
</script>

<template>
  <section class="backtest-view">
    <h1>量化回测</h1>

    <form class="inline-form" @submit.prevent="runBacktest">
      <label>
        股票代码
        <input v-model="form.symbol" placeholder="如 603893.SH" required />
      </label>
      <label>
        短均线
        <input v-model.number="form.short_window" type="number" min="2" max="250" />
      </label>
      <label>
        长均线
        <input v-model.number="form.long_window" type="number" min="2" max="500" />
      </label>
      <button type="submit" :disabled="loading">运行回测</button>
    </form>

    <p v-if="loading">计算中…</p>
    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="result" class="result">
      <div class="metric-grid">
        <dl>
          <dt>K 线数</dt>
          <dd>{{ result.metrics.bars }}</dd>
        </dl>
        <dl>
          <dt>买入持有收益</dt>
          <dd>{{ pct(result.metrics.buy_hold_return) }}</dd>
        </dl>
        <dl>
          <dt>策略收益</dt>
          <dd>{{ pct(result.metrics.strategy_return) }}</dd>
        </dl>
        <dl>
          <dt>年化收益</dt>
          <dd>{{ pct(result.metrics.annualized_return) }}</dd>
        </dl>
        <dl>
          <dt>最大回撤</dt>
          <dd>{{ pct(result.metrics.max_drawdown) }}</dd>
        </dl>
        <dl>
          <dt>交易次数</dt>
          <dd>{{ result.metrics.trades }}</dd>
        </dl>
      </div>
      <div ref="chartRef" class="curve-chart"></div>
    </div>
  </section>
</template>

<style scoped>
.inline-form {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.inline-form label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.9rem;
}

.inline-form input {
  padding: 0.4rem 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
}

.inline-form button {
  padding: 0.45rem 0.9rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #f3f4f6;
  cursor: pointer;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.metric-grid dl {
  margin: 0;
  padding: 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.metric-grid dt {
  color: #6b7280;
  font-size: 0.85rem;
}

.metric-grid dd {
  margin: 0.25rem 0 0;
  font-size: 1.2rem;
  font-weight: 600;
}

.curve-chart {
  width: 100%;
  height: 420px;
}

.error {
  color: #b91c1c;
}
</style>
