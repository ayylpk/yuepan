<script setup lang="ts">
// 每页顶部的全幅横幅:图 + 底部深海渐变压字(小帽英文 + 中文大标题)。
// 图未加载时先露同色渐变占位,加载完淡入 —— 首屏不闪白块。
import { ref } from 'vue'

defineProps<{
  img: string
  eyebrow: string
  title: string
}>()

const loaded = ref(false)
</script>

<template>
  <header class="page-hero" :style="{ background: 'linear-gradient(160deg, var(--sky), var(--sea-mid))' }">
    <img v-if="img" :src="img" :alt="title" :class="{ ready: loaded }" @load="loaded = true" />
    <div class="hero-caption">
      <p class="eyebrow">{{ eyebrow }}</p>
      <h1 class="hero-title">{{ title }}</h1>
      <slot />
    </div>
  </header>
</template>

<style scoped>
.page-hero > img {
  opacity: 0;
  transition: opacity 0.6s ease;
}
.page-hero > img.ready { opacity: 1; }
</style>
