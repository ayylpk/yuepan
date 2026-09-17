<script setup lang="ts">
// 根组件:初始化四季皮肤 + 顶层页转场。
// 注意分层:这里只负责 登录页/404 ↔ 主站壳 之间的淡入淡出;
// 壳内五页互切的转场在 SiteLayout 的内层 router-view(9/17 重塑修的挂载点——
// 旧版把 transition 挂在这层,壳内换页顶层组件始终是 SiteLayout,压根不触发)。
import { useRoute } from 'vue-router'
import { useSeasonStore } from '@/stores/season'

useSeasonStore().init()

const route = useRoute()
</script>

<template>
  <router-view v-slot="{ Component }">
    <transition name="route" mode="out-in">
      <!-- key 取顶层匹配路径:壳内子路由换页不让整壳重挂 -->
      <component :is="Component" :key="route.matched[0]?.path ?? route.path" />
    </transition>
  </router-view>
</template>
