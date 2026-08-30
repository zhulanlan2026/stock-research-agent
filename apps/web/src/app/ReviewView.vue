<script setup lang="ts">
import { ref } from 'vue';

type ReviewItem = { id: string; target: string; status: string };

const items = ref<ReviewItem[]>([
  { id: 'review-1', target: 'report-1', status: 'REVIEW_REQUIRED' },
  { id: 'review-2', target: 'report-2', status: 'UNDER_REVIEW' },
]);

function decide(id: string, decision: string): void {
  const item = items.value.find((entry) => entry.id === id);
  if (item) {
    item.status = decision;
  }
}
</script>

<template>
  <section class="review-view">
    <h1>人工审核</h1>
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>对象</th>
          <th>状态</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id">
          <td>{{ item.id }}</td>
          <td>{{ item.target }}</td>
          <td>{{ item.status }}</td>
          <td>
            <button @click="decide(item.id, 'APPROVED')">通过</button>
            <button @click="decide(item.id, 'NEEDS_REVISION')">退回</button>
            <button @click="decide(item.id, 'REJECTED')">拒绝</button>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.review-view table {
  width: 100%;
  border-collapse: collapse;
}

.review-view th,
.review-view td {
  border: 1px solid #e5e7eb;
  padding: 0.5rem;
  text-align: left;
}
</style>
