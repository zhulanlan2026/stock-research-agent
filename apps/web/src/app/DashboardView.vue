<script setup lang="ts">
import { useAuthStore } from '../stores/auth';

const auth = useAuthStore();
</script>

<template>
  <section>
    <h1>研股工作台</h1>
    <p>当前登录：{{ auth.user?.email }}</p>
  </section>
</template>
