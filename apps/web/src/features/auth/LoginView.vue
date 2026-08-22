<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { useAuthStore } from '../../stores/auth';

const email = ref('');
const password = ref('');
const error = ref('');
const loading = ref(false);

const auth = useAuthStore();
const router = useRouter();

async function submit(): Promise<void> {
  loading.value = true;
  error.value = '';
  try {
    await auth.login(email.value, password.value);
    await router.push('/');
  } catch {
    error.value = '登录失败，请检查邮箱和密码';
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="login-view">
    <form class="login-form" @submit.prevent="submit">
      <h1>stock-research-platform</h1>
      <label>
        邮箱
        <input v-model="email" type="email" required />
      </label>
      <label>
        密码
        <input v-model="password" type="password" required minlength="8" />
      </label>
      <p v-if="error" class="error">
        {{ error }}
      </p>
      <button type="submit" :disabled="loading">
        {{ loading ? '登录中…' : '登录' }}
      </button>
    </form>
  </main>
</template>

<style scoped>
.login-view {
  padding: 2rem;
  font-family: system-ui, sans-serif;
}

.login-form {
  display: grid;
  gap: 1rem;
  max-width: 20rem;
}

.login-form label {
  display: grid;
  gap: 0.25rem;
}

.error {
  color: #b91c1c;
}
</style>
