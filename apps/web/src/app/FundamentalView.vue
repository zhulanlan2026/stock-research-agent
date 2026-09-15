<script setup lang="ts">
import { ref } from 'vue';

import { http } from '../api/client';

type FundamentalAnalysisResponse = {
  symbol: string;
  as_of: string;
  coverage: number;
  summary: string;
  metrics: Record<string, string | null>;
  ratios: Record<string, string | null>;
};

const symbol = ref('600519.SH');
const loading = ref(false);
const error = ref('');
const result = ref<FundamentalAnalysisResponse | null>(null);

function errorMessage(err: unknown, fallback: string): string {
  if (typeof err !== 'object' || err === null) {
    return fallback;
  }
  const response = (err as { response?: { data?: { detail?: { message?: string } } } }).response;
  return response?.data?.detail?.message || fallback;
}

async function analyze(): Promise<void> {
  loading.value = true;
  error.value = '';
  result.value = null;
  try {
    const { data } = await http.post<FundamentalAnalysisResponse>('/fundamental/analysis', {
      symbol: symbol.value,
    });
    result.value = data;
  } catch (err: unknown) {
    error.value = errorMessage(err, '基本面分析失败');
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <section class="fundamental-view">
    <h1>基本面分析</h1>
    <p>基于财务事实、财务比率和估值快照的确定性基本面分析。</p>

    <form class="analysis-form" @submit.prevent="analyze">
      <label>
        股票代码
        <input v-model="symbol" placeholder="例如 600519.SH" />
      </label>
      <button type="submit" :disabled="loading">
        {{ loading ? '分析中…' : '开始分析' }}
      </button>
    </form>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="result" class="result">
      <div class="result-header">
        <h2>{{ result.symbol }}</h2>
        <p class="meta">
          as_of: {{ result.as_of }} · coverage: {{ result.coverage }}
        </p>
      </div>

      <p class="summary">{{ result.summary }}</p>

      <section class="panel">
        <h3>财务指标</h3>
        <dl class="metrics">
          <div v-for="(value, key) in result.metrics" :key="key">
            <dt>{{ key }}</dt>
            <dd>{{ value ?? '—' }}</dd>
          </div>
        </dl>
      </section>

      <section class="panel">
        <h3>财务比率</h3>
        <dl class="metrics">
          <div v-for="(value, key) in result.ratios" :key="key">
            <dt>{{ key }}</dt>
            <dd>{{ value ?? '—' }}</dd>
          </div>
        </dl>
      </section>
    </div>
  </section>
</template>

<style scoped>
.analysis-form {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  margin: 1rem 0;
}

.analysis-form label {
  display: grid;
  gap: 0.25rem;
}

.error {
  color: #b91c1c;
}

.result-header {
  margin-top: 1rem;
}

.meta {
  color: #6b7280;
  font-size: 0.85rem;
}

.summary {
  padding: 0.75rem;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 4px;
}

.panel {
  margin-top: 1rem;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.75rem;
  margin: 0;
}

.metrics div {
  padding: 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.metrics dt {
  color: #6b7280;
  font-size: 0.85rem;
}

.metrics dd {
  margin: 0.25rem 0 0;
  font-weight: 600;
}
</style>
