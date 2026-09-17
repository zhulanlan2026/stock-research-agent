<script setup lang="ts">
import { computed, ref } from 'vue';

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
  narrative: string | null;
  sections: ReportSection[];
};

const symbol = ref('600519.SH');
const mode = ref('standard');
const loading = ref(false);
const error = ref('');
const report = ref<ReportResponse | null>(null);
const activeTab = ref('综合报告');

const tabs = computed(() => {
  if (!report.value) {
    return [];
  }
  return ['综合报告', ...report.value.sections.map((section) => section.title)];
});

const activeSection = computed(() => {
  if (!report.value) {
    return null;
  }
  return report.value.sections.find((section) => section.title === activeTab.value) ?? null;
});

const activeData = computed<Record<string, unknown>>(() => activeSection.value?.data ?? {});

function displayMap(value: unknown): Record<string, string> {
  if (typeof value !== 'object' || value === null) {
    return {};
  }
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).map(([key, item]) => [
      key,
      item === null || item === undefined ? '—' : String(item),
    ]),
  );
}

function displayList(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

type GraphEvidenceItem = {
  source: string;
  predicate: string;
  target: string;
  score: number;
};

function graphEvidence(value: unknown): GraphEvidenceItem[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => item as GraphEvidenceItem);
}

type RagStep = {
  query: string;
  evidence_ids: string[];
};

function ragSteps(value: unknown): RagStep[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => item as RagStep);
}

function ragAgenticData(value: unknown): { evidence_ids: string[]; steps: RagStep[] } {
  const record = value as { evidence_ids?: unknown; steps?: unknown } | null | undefined;
  return {
    evidence_ids: Array.isArray(record?.evidence_ids)
      ? record.evidence_ids.map((item) => String(item))
      : [],
    steps: ragSteps(record?.steps),
  };
}

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
    const { data } = await http.post<ReportResponse>('/research/reports/comprehensive', {
      symbol: symbol.value,
      mode: mode.value,
    });
    report.value = data;
    activeTab.value = '综合报告';
  } catch (err: unknown) {
    error.value = errorMessage(err, '生成报告失败');
  } finally {
    loading.value = false;
  }
}

function selectTab(tab: string): void {
  activeTab.value = tab;
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

      <nav class="report-tabs">
        <button
          v-for="tab in tabs"
          :key="tab"
          type="button"
          :class="{ active: activeTab === tab }"
          @click="selectTab(tab)"
        >
          {{ tab }}
        </button>
      </nav>

      <div v-if="activeTab === '综合报告'" class="report-overview">
        <p class="summary">{{ report.summary }}</p>
        <p v-if="report.narrative" class="narrative">{{ report.narrative }}</p>
      </div>

      <div v-else-if="activeSection?.title === '专业财务'" class="report-section">
        <h3>专业财务</h3>
        <div class="metric-grid">
          <dl v-for="(value, key) in displayMap(activeData.metrics)" :key="key">
            <dt>{{ key }}</dt>
            <dd>{{ value }}</dd>
          </dl>
        </div>
        <h4>同比</h4>
        <div class="metric-grid">
          <dl v-for="(value, key) in displayMap(activeData.growth)" :key="key">
            <dt>{{ key }}</dt>
            <dd>{{ value }}</dd>
          </dl>
        </div>
        <h4>杜邦分析</h4>
        <div class="metric-grid">
          <dl v-for="(value, key) in displayMap(activeData.dupont)" :key="key">
            <dt>{{ key }}</dt>
            <dd>{{ value }}</dd>
          </dl>
        </div>
        <p class="muted">自由现金流：{{ activeData.free_cash_flow ?? '—' }}</p>
        <h4>财务风险点</h4>
        <ul v-if="displayList(activeData.risk_points).length > 0" class="risk-list">
          <li v-for="risk in displayList(activeData.risk_points)" :key="risk">{{ risk }}</li>
        </ul>
        <p v-else class="muted">暂无风险点</p>
      </div>

      <div v-else-if="activeSection?.title === 'RAG 证据'" class="report-section">
        <h3>RAG 证据</h3>
        <h4>Graph 证据</h4>
        <table v-if="graphEvidence(activeData.graph_evidence).length > 0" class="data-table">
          <thead>
            <tr>
              <th>来源</th>
              <th>关系</th>
              <th>目标</th>
              <th>得分</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="edge in graphEvidence(activeData.graph_evidence)" :key="`${edge.source}-${edge.target}`">
              <td>{{ edge.source }}</td>
              <td>{{ edge.predicate }}</td>
              <td>{{ edge.target }}</td>
              <td>{{ edge.score.toFixed(4) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="muted">暂无 Graph 证据</p>

        <h4>Agentic RAG</h4>
        <p class="muted">证据 ID：{{ ragAgenticData(activeData.agentic_rag).evidence_ids.join(', ') || '—' }}</p>
        <ol class="rag-steps">
          <li v-for="step in ragAgenticData(activeData.agentic_rag).steps" :key="step.query">
            <strong>{{ step.query }}</strong>
            <p>{{ step.evidence_ids.join(', ') || '—' }}</p>
          </li>
        </ol>
      </div>

      <div v-else-if="activeSection" class="report-section">
        <h3>{{ activeSection.title }}</h3>
        <pre>{{ JSON.stringify(activeSection.data, null, 2) }}</pre>
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

.report-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 1rem 0;
}

.report-tabs button {
  border: 1px solid #d1d5db;
  background: #ffffff;
  padding: 0.45rem 0.75rem;
  border-radius: 999px;
  cursor: pointer;
}

.report-tabs button.active {
  background: #1d4ed8;
  border-color: #1d4ed8;
  color: #ffffff;
}

.report-overview {
  margin-top: 1rem;
}

.summary {
  padding: 0.75rem;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 4px;
}

.narrative {
  padding: 0.75rem;
  background: #fefce8;
  border: 1px solid #fde047;
  border-radius: 4px;
  white-space: pre-wrap;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.75rem;
  margin: 0.5rem 0 1rem;
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
  font-weight: 600;
}

.muted {
  color: #6b7280;
}

.risk-list {
  margin: 0.5rem 0;
  padding-left: 1.2rem;
  color: #b91c1c;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.5rem 0 1rem;
}

.data-table th,
.data-table td {
  border: 1px solid #e5e7eb;
  padding: 0.45rem 0.6rem;
  text-align: left;
}

.rag-steps {
  margin: 0.5rem 0;
  padding-left: 1.2rem;
}

.rag-steps p {
  margin: 0.2rem 0 0.5rem;
  color: #6b7280;
}
</style>
