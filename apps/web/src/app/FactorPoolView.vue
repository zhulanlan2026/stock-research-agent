<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { http } from '../api/client';

type FactorDefinition = {
  name: string;
  category: string;
  description: string;
};

type FactorValue = {
  name: string;
  category: string;
  value: string | null;
};

type FactorPoolResponse = {
  symbol: string;
  as_of: string;
  factors: FactorValue[];
};

const symbol = ref('603893.SH');
const definitions = ref<FactorDefinition[]>([]);
const result = ref<FactorPoolResponse | null>(null);
const loading = ref(false);
const error = ref('');

const CATEGORY_LABELS: Record<string, string> = {
  quality: '质量因子',
  valuation: '估值因子',
  size: '规模因子',
  momentum: '动量因子',
  risk: '风险因子',
};

function errorMessage(err: unknown, fallback: string): string {
  if (typeof err !== 'object' || err === null) {
    return fallback;
  }
  const response = (err as { response?: { data?: { detail?: { message?: string } } } }).response;
  return response?.data?.detail?.message || fallback;
}

function description(name: string): string {
  return definitions.value.find((item) => item.name === name)?.description ?? name;
}

function formatValue(value: string | null): string {
  if (value === null || value === undefined) {
    return '—';
  }
  const num = Number(value);
  if (Number.isNaN(num)) {
    return value;
  }
  return Math.abs(num) >= 100000 ? num.toLocaleString() : num.toFixed(2);
}

function groupedFactors(): Array<{ category: string; label: string; items: FactorValue[] }> {
  if (!result.value) {
    return [];
  }
  const order = ['quality', 'valuation', 'size', 'momentum', 'risk'];
  return order
    .filter((category) => result.value?.factors.some((item) => item.category === category))
    .map((category) => ({
      category,
      label: CATEGORY_LABELS[category] ?? category,
      items: result.value!.factors.filter((item) => item.category === category),
    }));
}

async function loadDefinitions(): Promise<void> {
  try {
    const { data } = await http.get<FactorDefinition[]>('/factors');
    definitions.value = data;
  } catch (err: unknown) {
    error.value = errorMessage(err, '加载因子定义失败');
  }
}

async function computeFactors(): Promise<void> {
  loading.value = true;
  error.value = '';
  result.value = null;
  try {
    const { data } = await http.get<FactorPoolResponse>(`/factors/${symbol.value.trim()}`);
    result.value = data;
  } catch (err: unknown) {
    error.value = errorMessage(err, '计算因子失败');
  } finally {
    loading.value = false;
  }
}

onMounted(loadDefinitions);
</script>

<template>
  <section class="factor-view">
    <h1>因子池</h1>

    <form class="inline-form" @submit.prevent="computeFactors">
      <input v-model="symbol" placeholder="股票代码（如 603893.SH）" required />
      <button type="submit" :disabled="loading">计算因子</button>
    </form>

    <p v-if="loading">计算中…</p>
    <p v-if="error" class="error">{{ error }}</p>

    <div v-for="group in groupedFactors()" :key="group.category" class="factor-group">
      <h2>{{ group.label }}</h2>
      <table>
        <thead>
          <tr>
            <th>因子</th>
            <th>值</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in group.items" :key="item.name">
            <td>{{ description(item.name) }}</td>
            <td>{{ formatValue(item.value) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.inline-form {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.inline-form input {
  flex: 0 0 220px;
  padding: 0.4rem 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
}

.inline-form button {
  padding: 0.4rem 0.9rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #f3f4f6;
  cursor: pointer;
}

.factor-group {
  margin-bottom: 1rem;
}

.factor-group h2 {
  font-size: 1rem;
  margin: 0 0 0.4rem;
}

.factor-group table {
  width: 100%;
  border-collapse: collapse;
}

.factor-group th,
.factor-group td {
  border: 1px solid #e5e7eb;
  padding: 0.4rem 0.6rem;
  text-align: left;
}

.error {
  color: #b91c1c;
}
</style>
