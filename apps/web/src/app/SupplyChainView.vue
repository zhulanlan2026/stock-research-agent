<script setup lang="ts">
import * as echarts from 'echarts';
import { onMounted, ref } from 'vue';

import { http } from '../api/client';

const chartRef = ref<HTMLDivElement | null>(null);
const loading = ref(false);
const error = ref('');

let chart: echarts.ECharts | null = null;

async function loadGraph(): Promise<void> {
  loading.value = true;
  error.value = '';
  try {
    const { data } = await http.get('/supply-chain/graph');
    renderGraph(data.nodes, data.edges);
  } catch (err: any) {
    error.value = err?.response?.data?.detail?.message || '加载供应链图失败';
  } finally {
    loading.value = false;
  }
}

function renderGraph(nodes: string[], edges: any[]): void {
  if (!chartRef.value) {
    return;
  }
  if (!chart) {
    chart = echarts.init(chartRef.value);
  }
  chart.setOption({
    title: { text: '供应链图' },
    tooltip: {},
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        data: nodes.map((name) => ({ id: name, name })),
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

onMounted(loadGraph);
</script>

<template>
  <section class="supply-chain-view">
    <h1>供应链图</h1>
    <p v-if="loading">加载中…</p>
    <p v-if="error" class="error">{{ error }}</p>
    <div ref="chartRef" class="graph-chart"></div>
  </section>
</template>

<style scoped>
.supply-chain-view {
  height: calc(100vh - 130px);
}

.graph-chart {
  width: 100%;
  height: 100%;
  min-height: 500px;
}

.error {
  color: #b91c1c;
}
</style>
