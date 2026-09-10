<script setup lang="ts">
import { ref } from 'vue';

import { http } from '../api/client';
import { useAuthStore } from '../stores/auth';

const auth = useAuthStore();

type ReportSection = {
  title: string;
  data: Record<string, unknown>;
};

type ReportResponse = {
  symbol: string;
  as_of: string;
  module_version: string;
  summary: string;
  sections: ReportSection[];
};

type FundamentalAnalysisResponse = {
  summary: string;
  metrics: Record<string, unknown>;
  ratios: Record<string, unknown>;
};

const symbol = ref('600519.SH');
const mode = ref('standard');
const loading = ref(false);
const error = ref('');
const report = ref<ReportResponse | null>(null);
const faSymbol = ref('600519.SH');
const faLoading = ref(false);
const faError = ref('');
const faResult = ref<FundamentalAnalysisResponse | null>(null);

function errorMessage(err: unknown, fallback: string): string {
  if (typeof err !== 'object' || err === null) {
    return fallback;
  }
  const response = (err as { response?: { data?: { detail?: { message?: string } } } }).response;
  return response?.data?.detail?.message || fallback;
}

async function generateReport(): Promise<void> {
  loading.value = true;
  error.value = '';
  report.value = null;
  try {
    const { data } = await http.post<ReportResponse>('/research/reports', {
      symbol: symbol.value,
      mode: mode.value,
    });
    report.value = data;
  } catch (err: unknown) {
    error.value = errorMessage(err, '生成报告失败');
  } finally {
    loading.value = false;
  }
}

async function analyzeFundamental(): Promise<void> {
  faLoading.value = true;
  faError.value = '';
  faResult.value = null;
  try {
    const { data } = await http.post<FundamentalAnalysisResponse>('/fundamental/analysis', {
      symbol: faSymbol.value,
    });
    faResult.value = data;
  } catch (err: unknown) {
    faError.value = errorMessage(err, '财务分析失败');
  } finally {
    faLoading.value = false;
  }
}
</script>

<template>
  <section class="dashboard">
    <h1>研股工作台</h1>
    <p>当前登录：{{ auth.user?.email }}</p>

    <div class="report-form">
      <label>
        股票代码
        <input v-model="faSymbol" placeholder="例如 600519.SH" />
      </label>
      <button type="button" :disabled="faLoading" @click="analyzeFundamental">
        {{ faLoading ? '分析中…' : '财务分析' }}
      </button>
    </div>

    <p v-if="faError" class="error">{{ faError }}</p>

    <div v-if="faResult" class="report-section">
      <h3>财务分析</h3>
      <p class="summary">{{ faResult.summary }}</p>
      <pre>{{
        JSON.stringify({ metrics: faResult.metrics, ratios: faResult.ratios }, null, 2)
      }}</pre>
    </div>

    <div class="report-form">
      <label>
        股票代码
        <input v-model="symbol" placeholder="例如 600519.SH" />
      </label>
      <label>
        模式
        <select v-model="mode">
          <option value="quick">quick</option>
          <option value="standard">standard</option>
          <option value="deep">deep</option>
        </select>
      </label>
      <button type="button" :disabled="loading" @click="generateReport">
        {{ loading ? '生成中…' : '生成报告' }}
      </button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="report" class="report">
      <h2>报告：{{ report.symbol }}</h2>
      <p class="meta">as_of: {{ report.as_of }} · {{ report.module_version }}</p>
      <p class="summary">{{ report.summary }}</p>
      <div v-for="section in report.sections" :key="section.title" class="report-section">
        <h3>{{ section.title }}</h3>
        <pre>{{ JSON.stringify(section.data, null, 2) }}</pre>
      </div>
    </div>
  </section>
</template>

<style scoped>
.report-form {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  margin: 1rem 0;
}

.report-form label {
  display: grid;
  gap: 0.25rem;
}

.error {
  color: #b91c1c;
}

.report-section {
  margin: 1rem 0;
}

.report-section pre {
  background: #f5f5f5;
  padding: 0.75rem;
  border-radius: 4px;
  overflow-x: auto;
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
</style>
