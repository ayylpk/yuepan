<script setup lang="ts">
// 404:整屏落水图,一句话指路,不卖萌不写"哎呀"。
import { useRouter } from 'vue-router'
import { asset } from '@/stores/season'

const router = useRouter()
</script>

<template>
  <div class="nf" :style="{ backgroundImage: `url(${asset('page404')})` }">
    <div class="nf-card glass-card">
      <h1>404</h1>
      <p>这个地址没有对应的页面。</p>
      <div class="nf-actions">
        <t-button theme="primary" @click="router.replace('/')">回首页</t-button>
        <t-button variant="outline" @click="router.back()">上一页</t-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.nf {
  min-height: 100vh;
  display: flex; align-items: center; justify-content: center;
  background-size: cover; background-position: center;
  background-color: var(--sky);
}
.nf-card { width: min(360px, 90vw); text-align: center; padding: 36px 30px; }
.nf-card h1 {
  margin: 0; font-size: 64px; letter-spacing: 0.1em; color: var(--brand);
  font-family: var(--font-mono); font-weight: 700;
}
.nf-card p { margin: 6px 0 20px; color: var(--ink-soft); }
.nf-actions { display: flex; gap: 12px; justify-content: center; }
</style>
