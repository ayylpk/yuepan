<script setup lang="ts">
// 项目展示:数据来自 /api/projects(后端 project 三层已落地;挂载管理在设置页)。
// 9/17 重塑批2:PageHero→StageHero 全屏舞台,内容抬进 .page-floor 地板带。
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '@/api/http'
import type { Project } from '@/api/types'
import { asset } from '@/stores/season'
import StageHero from '@/components/StageHero.vue'

const router = useRouter()
const projects = ref<Project[]>([])
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    projects.value = await http.get<Project[]>('/api/projects')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <StageHero
      variant="banner" :img="asset('banner-projects')" title="项目"
      en="projects · on the wall" line="做过什么,值什么,都摆在这面墙上"
    />

    <div class="site-main">
        <t-loading :loading="loading" class="load-region">
          <p v-if="error" class="load-error">{{ error }} —— /api/projects 没接上,检查后端是否启动</p>
          <div v-else-if="projects.length" class="proj-grid stagger">
            <div v-for="(p, i) in projects" :key="p.id" class="card proj-card" :style="{ '--i': i }">
              <div class="proj-top">
                <span class="proj-code">{{ p.code }}</span>
                <div>
                  <h3>{{ p.name }}</h3>
                  <p class="period">{{ p.period }}</p>
                </div>
              </div>
              <p class="desc">{{ p.desc }}</p>
              <div class="techs">
                <span v-for="t in p.tech" :key="t" class="tech">{{ t }}</span>
              </div>
              <t-button
                v-if="p.repo" variant="outline" size="small" theme="primary"
                @click="router.push({ path: '/code', query: { repo: p.repo } })"
              >翻源码</t-button>
            </div>
          </div>
          <div v-else-if="!loading" class="empty-state">
            <img v-img-fade :src="asset('empty')" alt="空" loading="lazy" />
            <p>还没挂项目上去</p>
          </div>
        </t-loading>
    </div>
  </div>
</template>

<style scoped>
/* 加载期占位高度,数据到位前不塌缩跳动 */
.load-region { min-height: 260px; }
.proj-grid { display: grid; gap: 18px; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }
.proj-card {
  padding: 20px 22px; display: flex; flex-direction: column; gap: 12px; align-items: flex-start;
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
}
.proj-card:hover {
  transform: translateY(-3px);
  border-color: var(--brand);
  box-shadow: var(--card-shadow-hover);
}
.proj-top { display: flex; gap: 14px; align-items: center; }
.proj-code { font-size: 30px; }
.proj-top h3 { margin: 0; font-size: 18px; color: var(--ink); }
.period { margin: 2px 0 0; font-size: 12px; color: var(--ink-soft); }
.desc { margin: 0; font-size: 14px; line-height: 1.7; color: var(--ink-soft); }
.techs { display: flex; gap: 8px; flex-wrap: wrap; }
/* 技术栈小章:底色改吃季节云色,换季不再一身夏蓝 */
.tech {
  font-size: 12px; font-family: var(--font-mono);
  color: var(--sea-deep); background: color-mix(in srgb, var(--cloud) 55%, var(--card));
  padding: 2px 10px; border-radius: 999px;
}
.load-error { color: #c33; padding: 20px 0; }
</style>
