<script setup lang="ts">
import * as echarts from 'echarts';
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';

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
const radarRef = ref<HTMLDivElement | null>(null);
let radarChart: ReturnType<typeof echarts.init> | null = null;

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

function sectionDescription(title: string): string {
  const descriptions: Record<string, string> = {
    概览: '报告整体概览，包含数据覆盖度、模块版本和风险等级。',
    财务: '从财务事实计算营收、利润、ROE、ROA、负债结构等核心财务指标。',
    专业财务: '进一步展示同比增速、杜邦分析、自由现金流和财务风险点。',
    技术: '基于K线计算均线、MACD、RSI等技术指标。',
    周期分析: '使用FFT和小波分析识别价格主导周期。',
    行情: '当前市场快照、价格变化和样本覆盖情况。',
    供应链: '公司上下游供应链关系和图谱证据。',
    新闻: '公告与新闻事件的结构化摘要。',
    风险: '财务风险和市场风险的确定性聚合结果。',
    'RAG 证据': '标准RAG、Graph RAG和Agentic RAG检索到的证据链。',
    证据强度: '按证据等级和引用可用性计算证据强度。',
    版本信息: '报告与各模块版本记录。',
    免责声明: '报告使用边界和免责声明。',
  };
  return descriptions[title] ?? '结构化分析结果。';
}

function radarScore(section: ReportSection): number {
  const data = section.data;
  const coverage = Number(data.coverage ?? 0);
  const dataAvailable = data.data_available ? 1 : 0;
  const strength = Number(data.strength ?? 0);
  const pointCount = Number(data.point_count ?? 0);
  const sampleCount = Number(data.sample_count ?? 0);
  const itemCount = Number(data.item_count ?? 0);
  const risk = String(data.risk_level ?? '');

  if (data.strength !== undefined) {
    return Math.min(1, strength);
  }
  if (data.risk_level !== undefined) {
    if (risk === 'LOW') return 1;
    if (risk === 'MEDIUM') return 0.6;
    if (risk === 'HIGH') return 0.25;
  }
  if (pointCount > 0) return Math.min(1, pointCount / 100);
  if (sampleCount > 0) return Math.min(1, sampleCount / 20);
  if (itemCount > 0) return Math.min(1, itemCount / 20);
  return Math.min(1, coverage || dataAvailable);
}

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
    void nextTick(renderRadar);
  } catch (err: unknown) {
    error.value = errorMessage(err, '生成报告失败');
  } finally {
    loading.value = false;
  }
}

function renderRadar(): void {
  if (!radarRef.value || !report.value) {
    return;
  }
  const sections = report.value.sections.filter((section) =>
    ['财务', '专业财务', '技术', '行情', '供应链', '新闻', '风险', '证据强度'].includes(section.title),
  );
  if (sections.length === 0) {
    return;
  }
  const indicators = sections.map((section) => ({
    name: section.title,
    max: 1,
    score: radarScore(section),
  }));
  radarChart?.dispose();
  radarChart = echarts.init(radarRef.value);
  radarChart.setOption({
    tooltip: {},
    radar: {
      indicator: indicators.map((item) => ({ name: item.name, max: item.max })),
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: indicators.map((item) => item.score),
            name: '综合评分',
          },
        ],
      },
    ],
  });
}

watch(activeTab, (tab) => {
  if (tab === '综合报告') {
    void nextTick(renderRadar);
  }
});

onBeforeUnmount(() => {
  radarChart?.dispose();
});

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
        <div ref="radarRef" class="radar-chart"></div>
      </div>

      <div v-else-if="activeSection?.title === '专业财务'" class="report-section">
        <h3>专业财务</h3>
        <p class="section-description">{{ sectionDescription(activeSection.title) }}</p>
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
        <p class="section-description">{{ sectionDescription(activeSection.title) }}</p>
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
        <p class="section-description">{{ sectionDescription(activeSection.title) }}</p>
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

.section-description {
  color: #4b5563;
  margin: 0.5rem 0 1rem;
}

.radar-chart {
  width: 100%;
  height: 360px;
  margin-top: 1rem;
}
</style>
