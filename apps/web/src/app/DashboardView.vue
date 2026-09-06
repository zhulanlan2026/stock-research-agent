<script setup lang="ts">
import { ref } from 'vue';

import { http } from '../api/client';
import { useAuthStore } from '../stores/auth';

const auth = useAuthStore();

const symbol = ref('600519.SH');
const mode = ref('standard');
const loading = ref(false);
const error = ref('');
const report = ref<Record<string, any> | null>(null);

async function generateReport(): Promise<void> {
  loading.value = true;
  error.value = '';
  report.value = null;
  try {
    const { data } = await http.post('/research/reports', {
      symbol: symbol.value,
      mode: mode.value,
    });
    report.value = data;
  } catch (err: any) {
    error.value = err?.response?.data?.detail?.message || '生成报告失败';
  } finally {
    loading.value = false;
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
      <div
        v-for="section in report.sections"
        :key="section.title"
        class="report-section"
      >
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
</style>
