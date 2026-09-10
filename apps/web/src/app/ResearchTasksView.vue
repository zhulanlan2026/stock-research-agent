<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue';

import { getAccessToken, http } from '../api/client';

type TaskResponse = {
  id: string;
  status: string;
  symbol: string;
  mode: string;
  requested_modules: string[];
  question: string | null;
  created_at: string;
  updated_at: string;
};

type TaskEvent = {
  sequence_no: number;
  type: string;
  stage: string | null;
  message: string | null;
  created_at: string | null;
};

const availableModules = [
  'fundamental',
  'technical',
  'market',
  'supply_chain',
  'news',
  'risk',
  'research',
  'report',
  'review',
];

const symbol = ref('600519.SH');
const mode = ref('standard');
const question = ref('');
const selectedModules = ref<string[]>([
  'fundamental',
  'technical',
  'market',
  'supply_chain',
  'news',
  'risk',
  'research',
  'report',
  'review',
]);
const loading = ref(false);
const error = ref('');
const task = ref<TaskResponse | null>(null);
const events = ref<TaskEvent[]>([]);
let pollTimer: number | undefined;
let eventController: AbortController | null = null;
const apiBase = import.meta.env.VITE_API_BASE_URL || '/api/v1';

function errorMessage(err: unknown, fallback: string): string {
  if (typeof err !== 'object' || err === null) {
    return fallback;
  }
  const response = (err as { response?: { data?: { detail?: { message?: string } } } }).response;
  return response?.data?.detail?.message || fallback;
}

function isFinished(status: string): boolean {
  return ['completed', 'failed', 'rejected', 'review_required'].includes(status);
}

function toggleModule(name: string): void {
  const index = selectedModules.value.indexOf(name);
  if (index === -1) {
    selectedModules.value.push(name);
  } else {
    selectedModules.value.splice(index, 1);
  }
}

function stopPolling(): void {
  if (pollTimer !== undefined) {
    window.clearInterval(pollTimer);
    pollTimer = undefined;
  }
  stopEventStream();
}

function stopEventStream(): void {
  if (eventController !== null) {
    eventController.abort();
    eventController = null;
  }
}

async function createTask(): Promise<void> {
  loading.value = true;
  error.value = '';
  task.value = null;
  stopPolling();
  try {
    const { data } = await http.post<TaskResponse>('/research/tasks', {
      symbol: symbol.value,
      mode: mode.value,
      modules: selectedModules.value,
      question: question.value || null,
    });
    task.value = data;
    events.value = [];
    void startEventStream(data.id).catch((err: unknown) => {
      error.value = errorMessage(err, '事件流连接失败');
    });
    pollTimer = window.setInterval(() => {
      void refreshTask(data.id);
    }, 2000);
  } catch (err: unknown) {
    error.value = errorMessage(err, '创建研究任务失败');
  } finally {
    loading.value = false;
  }
}

async function refreshTask(id: string): Promise<void> {
  try {
    const { data } = await http.get<TaskResponse>(`/research/tasks/${id}`);
    task.value = data;
    if (isFinished(data.status)) {
      stopPolling();
    }
  } catch (err: unknown) {
    error.value = errorMessage(err, '加载研究任务失败');
    stopPolling();
  }
}

async function startEventStream(id: string): Promise<void> {
  stopEventStream();
  const controller = new AbortController();
  eventController = controller;
  const response = await fetch(`${apiBase}/research/tasks/${id}/events`, {
    headers: {
      Authorization: `Bearer ${getAccessToken() ?? ''}`,
    },
    signal: controller.signal,
  });
  if (!response.ok) {
    throw new Error('事件流请求失败');
  }
  if (!response.body) {
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split('\n\n');
    buffer = blocks.pop() ?? '';
    for (const block of blocks) {
      if (block.trim().length > 0) {
        events.value.push(...parseEvents(`${block}\n\n`));
      }
    }
  }
}

function parseEvents(text: string): TaskEvent[] {
  return text
    .split('\n\n')
    .filter((block) => block.trim().length > 0)
    .map((block) => {
      const dataLine = block.split('\n').find((line) => line.startsWith('data: '));
      if (!dataLine) {
        return null;
      }
      const payload = dataLine.slice('data: '.length);
      return JSON.parse(payload) as TaskEvent;
    })
    .filter((event): event is TaskEvent => event !== null);
}

onBeforeUnmount(stopPolling);
</script>

<template>
  <section class="tasks-view">
    <h1>研究任务</h1>

    <div class="task-form">
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
      <label>
        问题
        <input v-model="question" placeholder="可选研究问题" />
      </label>
      <button type="button" :disabled="loading" @click="createTask">
        {{ loading ? '创建中…' : '创建任务' }}
      </button>
    </div>

    <fieldset class="module-picker">
      <legend>执行模块</legend>
      <label v-for="name in availableModules" :key="name">
        <input
          type="checkbox"
          :checked="selectedModules.includes(name)"
          @change="toggleModule(name)"
        />
        {{ name }}
      </label>
    </fieldset>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="task" class="task-card">
      <h2>任务 {{ task.id }}</h2>
      <dl>
        <dt>标的</dt>
        <dd>{{ task.symbol }}</dd>
        <dt>模式</dt>
        <dd>{{ task.mode }}</dd>
        <dt>状态</dt>
        <dd>{{ task.status }}</dd>
        <dt>模块</dt>
        <dd>{{ task.requested_modules.join(', ') }}</dd>
        <dt>更新时间</dt>
        <dd>{{ task.updated_at }}</dd>
      </dl>
    </div>

    <div v-if="events.length > 0" class="event-timeline">
      <h2>执行事件</h2>
      <ol>
        <li v-for="event in events" :key="event.sequence_no">
          <strong>{{ event.type }}</strong>
          <span v-if="event.stage"> · {{ event.stage }}</span>
          <p v-if="event.message">{{ event.message }}</p>
          <time v-if="event.created_at">{{ event.created_at }}</time>
        </li>
      </ol>
    </div>
  </section>
</template>

<style scoped>
.task-form {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  margin: 1rem 0;
}

.task-form label {
  display: grid;
  gap: 0.25rem;
}

.module-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin: 1rem 0;
}

.module-picker label {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.task-card {
  margin-top: 1.5rem;
  padding: 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.task-card dl {
  display: grid;
  grid-template-columns: 6rem 1fr;
  gap: 0.4rem;
}

.task-card dd {
  margin: 0;
}

.error {
  color: #b91c1c;
}

.event-timeline {
  margin-top: 1.5rem;
}

.event-timeline ol {
  list-style: none;
  padding: 0;
}

.event-timeline li {
  border-left: 2px solid #bfdbfe;
  padding: 0.25rem 0.75rem;
  margin: 0.5rem 0;
}

.event-timeline time {
  color: #6b7280;
  font-size: 0.8rem;
}
</style>
