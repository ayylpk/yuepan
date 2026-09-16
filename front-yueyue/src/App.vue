<script setup lang="ts">
// 根组件:初始化四季皮肤,页面切换加一层淡入
import { onMounted } from 'vue'
import { useSeasonStore } from '@/stores/season'

useSeasonStore().init()
onMounted(() => {})
</script>

<template>
  <router-view v-slot="{ Component }">
    <transition name="page-fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>
