<script setup lang="ts">
import { useRouter } from 'vue-router';

import { useAuthStore } from '../stores/auth';

const auth = useAuthStore();
const router = useRouter();

async function logout(): Promise<void> {
  await auth.logout();
  await router.push('/login');
}
</script>

<template>
  <div class="layout">
    <header class="topbar">
      <span>stock-research-platform</span>
      <button type="button" @click="logout">退出</button>
    </header>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.topbar {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e5e7eb;
}

.content {
  padding: 1rem;
}
</style>
