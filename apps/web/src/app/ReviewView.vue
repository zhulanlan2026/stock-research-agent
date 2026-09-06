<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { http } from '../api/client';

type ReviewItem = {
  id: string;
  target_type: string;
  target_id: string;
  status: string;
  decision: string | null;
};

const items = ref<ReviewItem[]>([]);
const loading = ref(false);
const error = ref('');

async function loadQueue(): Promise<void> {
  loading.value = true;
  error.value = '';
  try {
    const { data } = await http.get('/reviews/queue');
    items.value = data;
  } catch (err: any) {
    error.value = err?.response?.data?.detail?.message || '加载审核队列失败';
  } finally {
    loading.value = false;
  }
}

async function decide(id: string, decision: string): Promise<void> {
  error.value = '';
  try {
    await http.post(`/reviews/${id}/decision`, { decision });
    await loadQueue();
  } catch (err: any) {
    error.value = err?.response?.data?.detail?.message || '提交决策失败';
  }
}

onMounted(loadQueue);
</script>

<template>
  <section class="review-view">
    <h1>人工审核</h1>
    <div class="toolbar">
      <button type="button" @click="loadQueue">刷新</button>
    </div>
    <p v-if="loading">加载中…</p>
    <p v-if="error" class="error">{{ error }}</p>
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
          <td>{{ item.target_type }}:{{ item.target_id }}</td>
          <td>{{ item.status }}</td>
          <td>
            <button @click="decide(item.id, 'APPROVED')">通过</button>
            <button @click="decide(item.id, 'NEEDS_REVISION')">退回</button>
            <button @click="decide(item.id, 'REJECTED')">拒绝</button>
          </td>
        </tr>
        <tr v-if="items.length === 0 && !loading">
          <td colspan="4">暂无待审核项</td>
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

.toolbar {
  margin: 0.75rem 0;
}

.error {
  color: #b91c1c;
}
</style>
