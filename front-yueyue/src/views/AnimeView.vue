<script setup lang="ts">
// 动漫 = 列表页(10/19 拆出):只出封面卡(作品名 + 简介摘要)与统计,点卡片进 /anime/:id。
// 新增作品仍在这里(建完直接跳进详情去补季与图片),编辑/删除/上传都搬到详情页。
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http } from '@/api/http'
import type { AnimeSummary } from '@/api/types'
import StageHero from '@/components/StageHero.vue'
import { asset } from '@/stores/season'

const router = useRouter()
const works = ref<AnimeSummary[]>([])
const loading = ref(true)
const creating = ref(false)
const saving = ref(false)
const form = reactive({ title: '', subtitle: '', description: '', visibility: 'public' })

async function load() {
  loading.value = true
  try {
    works.value = await http.get<AnimeSummary[]>('/api/anime')
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}
function startCreate() {
  Object.assign(form, { title: '', subtitle: '', description: '', visibility: 'public' })
  creating.value = true
}
async function save() {
  if (!form.title.trim()) return MessagePlugin.warning('请填写作品名称')
  saving.value = true
  try {
    const created = await http.post<{ id: number }>('/api/anime', { ...form })
    creating.value = false
    MessagePlugin.success('已建立，去补充季与图片')
    router.push(`/anime/${created.id}`)
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}
const excerpt = (w: AnimeSummary) => (w.description || '暂无简介').replace(/\s+/g, ' ').trim()
onMounted(load)
</script>
<template>
  <div>
    <StageHero variant="banner" :img="asset('banner-notes')" title="动漫收藏" en="anime · scenes & stories" line="每部作品独立整理，按季、按集留下画面和感想" />
    <div class="site-main">
      <div class="toolbar">
        <span class="hint">{{ works.length }} 部作品</span>
        <t-button theme="primary" @click="startCreate">新增作品</t-button>
      </div>
      <t-loading :loading="loading" class="load-region">
        <p v-if="!works.length" class="empty">还没有作品，添加一部开始整理。</p>
        <div class="work-list">
          <button
            v-for="work in works" :key="work.id"
            class="card work-card" type="button"
            @click="router.push(`/anime/${work.id}`)"
          >
            <span class="visibility">{{ work.visibility === 'private' ? '仅隐私小屋' : '公开展示' }}</span>
            <h2>{{ work.title }}</h2>
            <p v-if="work.subtitle" class="subtitle">{{ work.subtitle }}</p>
            <p class="excerpt">{{ excerpt(work) }}</p>
            <p class="meta">
              <span>{{ work.image_count }} 图</span>
              <span>{{ work.season_count }} 季</span>
              <span>{{ work.episode_count }} 集</span>
              <span class="go">进入</span>
            </p>
          </button>
        </div>
      </t-loading>
      <div v-if="creating" class="editor card">
        <div class="editor-head"><h2>新增作品</h2><t-button variant="text" @click="creating = false">关闭</t-button></div>
        <div class="form-grid">
          <t-input v-model="form.title" label="作品名称" />
          <t-input v-model="form.subtitle" label="副标题" />
          <t-select v-model="form.visibility" label="展示范围" :options="[{ label: '公开展示', value: 'public' }, { label: '仅隐私小屋', value: 'private' }]" />
        </div>
        <t-textarea v-model="form.description" label="作品简介" :autosize="{ minRows: 5 }" />
        <div class="editor-actions"><t-button theme="primary" :loading="saving" @click="save">保存作品</t-button></div>
      </div>
    </div>
  </div>
</template>
<style scoped>
.toolbar, .editor-head, .editor-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.toolbar { margin-bottom: 20px; }
.hint, .empty { color: var(--ink-soft); }
.load-region { min-height: 240px; display: block; }
.empty { padding: 36px 0; }
.work-list { display: grid; gap: 16px; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }
.work-card {
  display: flex; flex-direction: column; align-items: flex-start; gap: 6px;
  padding: 20px 22px; text-align: left; font: inherit; cursor: pointer;
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}
.work-card:hover {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--sea-mid) 55%, var(--card-line));
  box-shadow: 0 16px 34px -16px rgba(20, 90, 140, 0.32);
}
.work-card h2 { margin: 2px 0 0; font: 400 24px var(--font-display); letter-spacing: 0.04em; }
.subtitle { margin: 0; color: var(--ink-soft); font-size: 13px; }
.excerpt {
  margin: 8px 0 0; color: var(--ink-soft); font-size: 13.5px; line-height: 1.7;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
}
.meta { display: flex; align-items: center; gap: 12px; margin: 14px 0 0; width: 100%; font-size: 12.5px; color: var(--ink-soft); }
.meta .go { margin-left: auto; color: var(--brand); }
.visibility { font-size: 12px; color: var(--brand); }
.editor { position: fixed; z-index: 20; right: 24px; bottom: 24px; width: min(620px, calc(100vw - 32px)); max-height: calc(100vh - 48px); overflow: auto; padding: 22px; box-shadow: var(--shadow); }
.editor-head h2 { margin: 0; font-size: 20px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 18px 0; }
.editor-actions { justify-content: flex-end; margin-top: 18px; }
@media (max-width: 640px) { .form-grid { grid-template-columns: 1fr; } }
</style>
