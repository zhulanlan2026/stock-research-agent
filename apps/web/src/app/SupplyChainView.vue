<script setup lang="ts">
import * as echarts from 'echarts';
import { computed, onMounted, ref, watch } from 'vue';

import { http } from '../api/client';

const chartRef = ref<HTMLDivElement | null>(null);
const loading = ref(false);
const error = ref('');
const notice = ref('');
const selectedNode = ref('');
const activeTab = ref<'contracts' | 'aliases' | 'risk' | 'node'>('contracts');

const form = ref({
  subject_org: '',
  object_org: '',
  amount: '',
  currency: 'CNY',
});

const aliasForm = ref({
  canonical_name: '',
  alias: '',
});
const aliases = ref<Array<{ id: string; canonical_name: string; alias: string }>>([]);

const riskInput = ref('德福科技:1.0');
const riskSteps = ref(2);
const riskResult = ref<Record<string, number>>({});
const snapshots = ref<
  Array<{
    id: string;
    symbol: string | null;
    initial_risk: Record<string, number>;
    max_steps: number;
    damping: number;
    result: Record<string, number>;
    created_at: string;
  }>
>([]);
const selectedSnapshotId = ref('');
const compareA = ref('');
const compareB = ref('');
const contracts = ref<
  Array<{
    id: string;
    subject_org: string;
    object_org: string;
    amount: string;
    currency: string;
    status: string;
    evidence_ids: string[];
  }>
>([]);
const symbolInput = ref('');

let nodes: string[] = [];
let edges: Array<{ source: string; predicate: string; target: string }> = [];
let chart: echarts.ECharts | null = null;

const selectedSnapshot = computed(() =>
  snapshots.value.find((snapshot) => snapshot.id === selectedSnapshotId.value),
);

const compareRows = computed(() => {
  const a = snapshots.value.find((snapshot) => snapshot.id === compareA.value);
  const b = snapshots.value.find((snapshot) => snapshot.id === compareB.value);
  if (!a || !b) {
    return [];
  }
  const names = new Set([...Object.keys(a.result), ...Object.keys(b.result)]);
  return [...names].map((name) => ({
    name,
    a: a.result[name] ?? 0,
    b: b.result[name] ?? 0,
    diff: (b.result[name] ?? 0) - (a.result[name] ?? 0),
  }));
});

type GraphEdge = {
  source: string;
  predicate: string;
  target: string;
};

type GraphResponse = {
  nodes: string[];
  edges: GraphEdge[];
};

function errorMessage(err: unknown, fallback: string): string {
  if (typeof err !== 'object' || err === null) {
    return fallback;
  }
  const response = (err as { response?: { data?: { detail?: { message?: string } } } }).response;
  return response?.data?.detail?.message || fallback;
}

async function loadGraph(): Promise<void> {
  loading.value = true;
  error.value = '';
  try {
    const { data } = await http.get<GraphResponse>('/supply-chain/graph');
    nodes = data.nodes;
    edges = data.edges;
    renderGraph();
  } catch (err: unknown) {
    error.value = errorMessage(err, '加载供应链图失败');
  } finally {
    loading.value = false;
  }
}

function renderGraph(): void {
  if (!chartRef.value) {
    return;
  }
  if (!chart) {
    chart = echarts.init(chartRef.value);
    chart.on('click', (params: unknown) => {
      const p = params as { dataType?: string; name?: string };
      if (p.dataType === 'node' && p.name) {
        selectedNode.value = p.name;
        activeTab.value = 'node';
      }
    });
  }
  const maxRisk = Math.max(...Object.values(riskResult.value).filter((value) => value > 0), 0.001);
  chart.setOption({
    title: { text: '供应链图' },
    tooltip: {},
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        data: nodes.map((name) => {
          if (compareRows.value.length > 0) {
            const row = compareRows.value.find((item) => item.name === name);
            const diff = row?.diff ?? 0;
            const maxAbs = Math.max(
              ...compareRows.value.map((item) => Math.abs(item.diff)),
              0.001,
            );
            const symbolSize = 18 + (Math.abs(diff) / maxAbs) * 30;
            const lightness = 50 - (Math.abs(diff) / maxAbs) * 25;
            const color =
              diff >= 0
                ? `hsl(0, 70%, ${lightness}%)`
                : `hsl(120, 70%, ${lightness}%)`;
            return { id: name, name, symbolSize, itemStyle: { color } };
          }
          const risk = riskResult.value[name];
          const hasRisk = risk !== undefined;
          const symbolSize = hasRisk
            ? 18 + (Math.max(risk, 0) / maxRisk) * 30
            : name === selectedNode.value
              ? 34
              : 24;
          const color = hasRisk
            ? riskColor(risk, maxRisk)
            : name === selectedNode.value
              ? '#dc2626'
              : '#5470c6';
          return { id: name, name, symbolSize, itemStyle: { color } };
        }),
        links: edges.map((edge) => ({
          source: edge.source,
          target: edge.target,
          label: { show: true, formatter: edge.predicate },
        })),
        label: { show: true, position: 'right' },
        force: { repulsion: 120, edgeLength: 100 },
      },
    ],
  });
}

function riskColor(risk: number, max: number): string {
  const ratio = max > 0 ? Math.max(0, Math.min(1, risk / max)) : 0;
  const hue = Math.round(220 - 220 * ratio);
  return `hsl(${hue}, 70%, 50%)`;
}

async function submitContract(): Promise<void> {
  error.value = '';
  notice.value = '';
  try {
    await http.post('/supply-chain/contracts', {
      subject_org: form.value.subject_org.trim(),
      object_org: form.value.object_org.trim(),
      amount: form.value.amount,
      currency: form.value.currency,
      evidence_ids: [],
    });
    notice.value = '合同已保存，创建审核并通过后会自动发布到图谱';
    form.value.subject_org = '';
    form.value.object_org = '';
    form.value.amount = '';
  } catch (err: unknown) {
    error.value = errorMessage(err, '保存合同失败');
  }
}

async function createReview(): Promise<void> {
  error.value = '';
  notice.value = '';
  try {
    await http.post('/supply-chain/reviews', {});
    notice.value = '已创建审核，请到审核中心点击“通过”以发布图谱';
  } catch (err: unknown) {
    error.value = errorMessage(err, '创建审核失败');
  }
}

async function loadAliases(): Promise<void> {
  try {
    const { data } = await http.get('/supply-chain/organization-aliases');
    aliases.value = data;
  } catch (err: unknown) {
    error.value = errorMessage(err, '加载组织别名失败');
  }
}

async function deleteAlias(id: string): Promise<void> {
  error.value = '';
  try {
    await http.delete(`/supply-chain/organization-aliases/${id}`);
    await loadAliases();
  } catch (err: unknown) {
    error.value = errorMessage(err, '删除组织别名失败');
  }
}

async function loadContracts(): Promise<void> {
  try {
    const { data } = await http.get('/supply-chain/contracts');
    contracts.value = data;
  } catch (err: unknown) {
    error.value = errorMessage(err, '加载合同失败');
  }
}

async function resolveSymbol(): Promise<void> {
  error.value = '';
  notice.value = '';
  const symbol = symbolInput.value.trim();
  if (!symbol) {
    return;
  }
  try {
    const { data } = await http.get<{ organization: string }>(
      '/supply-chain/resolve-symbol',
      { params: { symbol } },
    );
    form.value.subject_org = data.organization;
    notice.value = `${symbol} → ${data.organization}`;
  } catch (err: unknown) {
    error.value = errorMessage(err, '解析股票代码失败');
  }
}

async function submitAlias(): Promise<void> {
  error.value = '';
  notice.value = '';
  try {
    await http.post('/supply-chain/organization-aliases', {
      canonical_name: aliasForm.value.canonical_name.trim(),
      alias: aliasForm.value.alias.trim(),
    });
    aliasForm.value.canonical_name = '';
    aliasForm.value.alias = '';
    await loadAliases();
    notice.value = '组织别名已保存';
  } catch (err: unknown) {
    error.value = errorMessage(err, '保存组织别名失败');
  }
}

function parseRiskInput(): Record<string, number> {
  const risk: Record<string, number> = {};
  for (const part of riskInput.value.split(',')) {
    const trimmed = part.trim();
    if (!trimmed) {
      continue;
    }
    const [node, value] = trimmed.split(':');
    const parsed = Number(value);
    if (node && !Number.isNaN(parsed)) {
      risk[node.trim()] = parsed;
    }
  }
  return risk;
}

async function propagateRisk(): Promise<void> {
  error.value = '';
  try {
    const { data } = await http.post<{ risk: Record<string, number> }>(
      '/supply-chain/risk-propagation',
      {
        initial_risk: parseRiskInput(),
        max_steps: riskSteps.value,
      },
    );
    riskResult.value = data.risk;
    renderGraph();
  } catch (err: unknown) {
    error.value = errorMessage(err, '风险传播计算失败');
  }
}

async function saveSnapshot(): Promise<void> {
  error.value = '';
  try {
    await http.post('/supply-chain/risk-snapshots', {
      initial_risk: parseRiskInput(),
      max_steps: riskSteps.value,
    });
    await loadSnapshots();
    notice.value = '风险快照已保存';
  } catch (err: unknown) {
    error.value = errorMessage(err, '保存风险快照失败');
  }
}

async function loadSnapshots(): Promise<void> {
  try {
    const { data } = await http.get('/supply-chain/risk-snapshots');
    snapshots.value = data;
  } catch (err: unknown) {
    error.value = errorMessage(err, '加载风险快照失败');
  }
}

async function deleteSnapshot(id: string): Promise<void> {
  error.value = '';
  try {
    await http.delete(`/supply-chain/risk-snapshots/${id}`);
    if (selectedSnapshotId.value === id) {
      selectedSnapshotId.value = '';
    }
    await loadSnapshots();
  } catch (err: unknown) {
    error.value = errorMessage(err, '删除快照失败');
  }
}

const selectedDetails = (): {
  incoming: GraphEdge[];
  outgoing: GraphEdge[];
  alias: string | undefined;
  risk: number | undefined;
  contracts: Array<{ amount: string; currency: string; counterparty: string; evidence_ids: string[] }>;
} => {
  const incoming = edges.filter((edge) => edge.target === selectedNode.value);
  const outgoing = edges.filter((edge) => edge.source === selectedNode.value);
  const alias = aliases.value.find((item) => item.alias === selectedNode.value)?.canonical_name;
  const relatedContracts = contracts.value
    .filter(
      (contract) =>
        contract.subject_org === selectedNode.value || contract.object_org === selectedNode.value,
    )
    .map((contract) => ({
      amount: contract.amount,
      currency: contract.currency,
      counterparty:
        contract.subject_org === selectedNode.value ? contract.object_org : contract.subject_org,
      evidence_ids: contract.evidence_ids,
    }));
  return {
    incoming,
    outgoing,
    alias,
    risk: riskResult.value[selectedNode.value],
    contracts: relatedContracts,
  };
};

onMounted(() => {
  void loadGraph();
  void loadAliases();
  void loadContracts();
  void loadSnapshots();
});

watch([compareA, compareB], () => {
  renderGraph();
});
</script>

<template>
  <section class="supply-chain-view">
    <div class="page-head">
      <h1>供应链图</h1>
      <button type="button" @click="loadGraph">刷新图</button>
    </div>

    <nav class="tabs">
      <button :class="{ active: activeTab === 'contracts' }" @click="activeTab = 'contracts'">
        合同
      </button>
      <button :class="{ active: activeTab === 'aliases' }" @click="activeTab = 'aliases'">
        组织别名
      </button>
      <button :class="{ active: activeTab === 'risk' }" @click="activeTab = 'risk'">
        风险分析
      </button>
      <button :class="{ active: activeTab === 'node' }" @click="activeTab = 'node'">
        节点详情
      </button>
    </nav>

    <div v-if="activeTab === 'contracts'" class="tab-panel">
      <div class="panel">
        <h2>新增合同</h2>
        <form class="inline-form" @submit.prevent="submitContract">
          <input v-model="symbolInput" placeholder="股票代码解析（如 301511.SZ）" />
          <button type="button" @click="resolveSymbol">解析</button>
          <input v-model="form.subject_org" placeholder="主体组织（如 德福科技）" required />
          <input v-model="form.object_org" placeholder="对象组织（如 宁德时代）" required />
          <input v-model="form.amount" placeholder="金额" required />
          <input v-model="form.currency" placeholder="币种" maxlength="8" />
          <button type="submit" :disabled="loading">保存合同</button>
          <button type="button" @click="createReview">创建审核</button>
        </form>
      </div>

      <div class="panel">
        <h2>合同列表</h2>
        <table v-if="contracts.length > 0" class="contract-table">
          <thead>
            <tr>
              <th>主体</th>
              <th>对象</th>
              <th>金额</th>
              <th>币种</th>
              <th>状态</th>
              <th>证据</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in contracts" :key="c.id">
              <td>{{ c.subject_org }}</td>
              <td>{{ c.object_org }}</td>
              <td>{{ c.amount }}</td>
              <td>{{ c.currency }}</td>
              <td>{{ c.status }}</td>
              <td>{{ c.evidence_ids.length }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else>暂无合同</p>
      </div>
    </div>

    <div v-if="activeTab === 'aliases'" class="tab-panel">
      <div class="panel">
        <h2>组织别名</h2>
        <form class="inline-form" @submit.prevent="submitAlias">
          <input v-model="aliasForm.canonical_name" placeholder="规范名（如 宁德时代新能源科技股份有限公司）" required />
          <input v-model="aliasForm.alias" placeholder="别名（如 宁德时代）" required />
          <button type="submit">保存别名</button>
        </form>
        <ul v-if="aliases.length > 0" class="alias-list">
          <li v-for="item in aliases" :key="item.id">
            {{ item.alias }} → {{ item.canonical_name }}
            <button type="button" @click="deleteAlias(item.id)">删除</button>
          </li>
        </ul>
      </div>
    </div>

    <div v-if="activeTab === 'risk'" class="tab-panel">
      <div class="panel">
        <h2>多跳风险传播</h2>
        <form class="inline-form" @submit.prevent="propagateRisk">
          <input v-model="riskInput" placeholder="初始风险（如 德福科技:1.0）" />
          <input v-model.number="riskSteps" type="number" min="1" max="100" />
          <button type="submit">计算</button>
          <button type="button" @click="saveSnapshot">保存快照</button>
        </form>
        <ul v-if="Object.keys(riskResult).length > 0" class="risk-list">
          <li v-for="(value, name) in riskResult" :key="name">{{ name }}: {{ value.toFixed(4) }}</li>
        </ul>
      </div>

      <div class="panel">
        <h2>风险快照历史</h2>
        <ul v-if="snapshots.length > 0" class="snapshot-list">
          <li
            v-for="s in snapshots"
            :key="s.id"
            :class="{ selected: s.id === selectedSnapshotId }"
            @click="selectedSnapshotId = s.id"
          >
            <span>
              {{ new Date(s.created_at).toLocaleString() }} · 步数 {{ s.max_steps }} ·
              {{ Object.keys(s.result).filter((k) => s.result[k] > 0).length }} 个风险节点
            </span>
            <button type="button" @click.stop="deleteSnapshot(s.id)">删除</button>
          </li>
        </ul>
        <p v-else>暂无快照</p>
      </div>

      <div v-if="selectedSnapshot" class="panel">
        <h2>快照详情</h2>
        <p>时间：{{ new Date(selectedSnapshot.created_at).toLocaleString() }}</p>
        <p>步数：{{ selectedSnapshot.max_steps }} · damping：{{ selectedSnapshot.damping }}</p>
        <p>初始风险：</p>
        <ul>
          <li v-for="(v, name) in selectedSnapshot.initial_risk" :key="name">{{ name }}: {{ v }}</li>
        </ul>
        <p>传播结果：</p>
        <ul>
          <li v-for="(v, name) in selectedSnapshot.result" :key="name">{{ name }}: {{ v.toFixed(4) }}</li>
        </ul>
      </div>

      <div class="panel">
        <h2>快照对比</h2>
        <div class="inline-form">
          <select v-model="compareA">
            <option value="" disabled>选择快照 A</option>
            <option v-for="s in snapshots" :key="s.id" :value="s.id">
              {{ new Date(s.created_at).toLocaleString() }}
            </option>
          </select>
          <select v-model="compareB">
            <option value="" disabled>选择快照 B</option>
            <option v-for="s in snapshots" :key="s.id" :value="s.id">
              {{ new Date(s.created_at).toLocaleString() }}
            </option>
          </select>
        </div>
        <table v-if="compareRows.length > 0" class="contract-table">
          <thead>
            <tr>
              <th>节点</th>
              <th>A</th>
              <th>B</th>
              <th>差值</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in compareRows" :key="row.name">
              <td>{{ row.name }}</td>
              <td>{{ row.a.toFixed(4) }}</td>
              <td>{{ row.b.toFixed(4) }}</td>
              <td>{{ row.diff.toFixed(4) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="activeTab === 'node'" class="tab-panel">
      <div v-if="selectedNode" class="panel">
        <h2>节点详情：{{ selectedNode }}</h2>
        <p v-if="selectedDetails().alias">规范名：{{ selectedDetails().alias }}</p>
        <p v-if="selectedDetails().risk !== undefined">风险值：{{ selectedDetails().risk?.toFixed(4) }}</p>
        <p>入边：{{ selectedDetails().incoming.map((e) => `${e.source} → ${e.predicate}`).join('；') || '无' }}</p>
        <p>出边：{{ selectedDetails().outgoing.map((e) => `${e.predicate} → ${e.target}`).join('；') || '无' }}</p>
        <div v-if="selectedDetails().contracts.length > 0">
          <p>相关合同：</p>
          <ul>
            <li v-for="c in selectedDetails().contracts" :key="`${c.counterparty}-${c.amount}`">
              {{ c.counterparty }}：{{ c.amount }} {{ c.currency }}（证据 {{ c.evidence_ids.length }} 条）
            </li>
          </ul>
        </div>
      </div>
      <p v-else>点击图上的节点查看详情</p>
    </div>

    <p v-if="notice" class="notice">{{ notice }}</p>
    <p v-if="loading">加载中…</p>
    <p v-if="error" class="error">{{ error }}</p>
    <div ref="chartRef" class="graph-chart"></div>
  </section>
</template>

<style scoped>
.supply-chain-view {
  min-height: calc(100vh - 130px);
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.page-head h1 {
  margin: 0;
}

.page-head button {
  padding: 0.4rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #f3f4f6;
  cursor: pointer;
}

.tabs {
  display: flex;
  gap: 0.25rem;
  margin-bottom: 0.75rem;
  border-bottom: 1px solid #e5e7eb;
}

.tabs button {
  padding: 0.4rem 0.9rem;
  border: none;
  background: transparent;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.tabs button.active {
  border-bottom-color: #1d4ed8;
  color: #1d4ed8;
  font-weight: 600;
}

.tab-panel {
  margin-bottom: 0.75rem;
}

.panel {
  margin-bottom: 0.75rem;
}

.panel h2 {
  font-size: 1rem;
  margin: 0 0 0.4rem;
}

.inline-form {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.inline-form input {
  flex: 1;
  min-width: 140px;
  padding: 0.4rem 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
}

.inline-form button {
  padding: 0.4rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #f3f4f6;
  cursor: pointer;
}

.graph-chart {
  width: 100%;
  min-height: 460px;
}

.alias-list,
.risk-list,
.snapshot-list {
  margin: 0.5rem 0 0;
  padding-left: 1.2rem;
}

.contract-table {
  width: 100%;
  border-collapse: collapse;
}

.contract-table th,
.contract-table td {
  border: 1px solid #e5e7eb;
  padding: 0.4rem 0.5rem;
  text-align: left;
  font-size: 0.9rem;
}

.snapshot-list li {
  cursor: pointer;
  padding: 0.15rem 0;
}

.snapshot-list li.selected {
  background: #eef2ff;
  font-weight: 600;
}

.notice {
  color: #15803d;
  margin: 0.25rem 0 0.5rem;
}

.error {
  color: #b91c1c;
}
</style>
