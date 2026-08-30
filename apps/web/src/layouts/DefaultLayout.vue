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
      <nav class="nav">
        <router-link to="/">工作台</router-link>
        <router-link to="/market">行情</router-link>
        <router-link to="/supply-chain">供应链</router-link>
        <button type="button" @click="logout">退出</button>
      </nav>
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
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e5e7eb;
}

.nav {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.content {
  padding: 1rem;
}
</style>
