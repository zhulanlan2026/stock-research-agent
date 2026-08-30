<script setup lang="ts">
import * as echarts from 'echarts';
import { onMounted, ref } from 'vue';

type GraphNode = { id: string; name: string };
type GraphEdge = { source: string; target: string; predicate: string };

const chartRef = ref<HTMLDivElement | null>(null);

const nodes: GraphNode[] = [
  { id: 'A', name: '贵州茅台' },
  { id: 'B', name: '供应商B' },
  { id: 'C', name: '客户C' },
];

const edges: GraphEdge[] = [
  { source: 'A', target: 'B', predicate: 'procured_from' },
  { source: 'A', target: 'C', predicate: 'sold_to' },
];

onMounted(() => {
  if (!chartRef.value) {
    return;
  }
  const chart = echarts.init(chartRef.value);
  chart.setOption({
    title: { text: '供应链图' },
    tooltip: {},
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        data: nodes.map((node) => ({ id: node.id, name: node.name })),
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
});
</script>

<template>
  <section class="supply-chain-view">
    <h1>供应链图</h1>
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
</style>
