<script setup lang="ts">
// 404(9/17 重塑批4):整屏落水图 + 暗压字,一句话指路,不卖萌不写"哎呀"。
import { useRouter } from 'vue-router'
import { asset } from '@/stores/season'

const router = useRouter()
</script>

<template>
  <div class="full-stage">
    <img v-img-fade class="full-stage__bg" :src="asset('page404')" alt="" />
    <div class="full-stage__scrim" aria-hidden="true" />

    <div class="nf-card glass-overlay">
      <h1>404</h1>
      <p class="nf-en">lost beyond the tide line</p>
      <p class="nf-say">这个地址没有对应的页面。</p>
      <div class="nf-actions">
        <t-button theme="primary" @click="router.replace('/')">回首页</t-button>
        <t-button variant="outline" @click="router.back()">上一页</t-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.nf-card {
  width: min(360px, 90vw); text-align: center; padding: 36px 30px;
  animation: copy-rise 0.8s 0.3s cubic-bezier(0.22, 0.61, 0.36, 1) backwards;
}
.nf-card h1 {
  margin: 0; font-size: clamp(56px, 9vw, 76px); font-weight: 400;
  letter-spacing: 0.12em; color: var(--brand);
  font-family: var(--font-display);
}
.nf-en {
  margin: 2px 0 0; font-family: var(--font-serif); font-style: italic;
  font-size: 13px; letter-spacing: 0.06em; color: var(--ink-soft);
}
.nf-say { margin: 14px 0 20px; color: var(--ink); }
.nf-actions { display: flex; gap: 12px; justify-content: center; }
</style>
