<script setup lang="ts">
// 顶栏四季切换器:四枚海色圆点,当前季描白圈。
// 春/冬配图未出:按钮在、逻辑在,但暂不绑定点击(disabled),
// 启用只需往 season.ts 的 SEASONS_IMAGE_READY 里加 key(9/17 拍板)。
import { SEASONS, hasSeasonImages, useSeasonStore } from '@/stores/season'
import type { Season } from '@/stores/season'

const season = useSeasonStore()
</script>

<template>
  <div class="season-dots" role="radiogroup" aria-label="切换季节">
    <button
      v-for="s in SEASONS" :key="s.key"
      class="dot" :class="{ active: season.season === s.key }"
      :style="{ background: s.dot, color: s.dot }"
      :disabled="!hasSeasonImages(s.key)"
      :title="hasSeasonImages(s.key) ? `${s.label}季皮肤` : `${s.label}季配图未出,暂不可选`"
      role="radio" :aria-checked="season.season === s.key"
      @click="season.set(s.key as Season)"
    />
  </div>
</template>

<style scoped>
.season-dots { display: flex; gap: 8px; }
.dot {
  width: 14px; height: 14px;
  border-radius: 50%; border: none; cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
  padding: 0;
}
.dot:not(:disabled):hover { transform: scale(1.25); }
.dot.active { box-shadow: 0 0 0 2px #fff, 0 0 0 4px currentColor; transform: scale(1.15); }
.dot:disabled { opacity: 0.3; cursor: not-allowed; }
</style>
