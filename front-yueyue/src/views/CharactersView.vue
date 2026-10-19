<script setup lang="ts">
// 人物志 = 列表页(10/19 拆出):每张卡 = 肖像缩略图 + 名字 + 副标题 + 简介一行,点卡片进 /characters/:id。
// 肖像取后端 cover_image_id 指向的那张;没设过就显示名字首字占位(不放图集第一张,语义不同)。
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http } from '@/api/http'
import type { CharacterSummary } from '@/api/types'
import StageHero from '@/components/StageHero.vue'
import { asset } from '@/stores/season'

const router = useRouter()
const rows = ref<CharacterSummary[]>([])
const loading = ref(true)
const creating = ref(false)
const saving = ref(false)
const form = reactive({
  name: '', subtitle: '', bio: '', visibility: 'public',
  fields: [{ label: '身高', value: '' }, { label: '体重', value: '' }, { label: '出自', value: '' }, { label: '爱好', value: '' }],
})

async function load() {
  loading.value = true
  try {
    rows.value = await http.get<CharacterSummary[]>('/api/characters')
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}
function startCreate() {
  Object.assign(form, {
    name: '', subtitle: '', bio: '', visibility: 'public',
    fields: [{ label: '身高', value: '' }, { label: '体重', value: '' }, { label: '出自', value: '' }, { label: '爱好', value: '' }],
  })
  creating.value = true
}
async function save() {
  if (!form.name.trim()) return MessagePlugin.warning('请填写人物名称')
  saving.value = true
  try {
    const created = await http.post<{ id: number }>('/api/characters', {
      ...form, fields: form.fields.filter(f => f.label.trim()),
    })
    creating.value = false
    MessagePlugin.success('已建立，去添加肖像与图片')
    router.push(`/characters/${created.id}`)
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}
const portrait = (row: CharacterSummary) => row.cover ?? null
const initial = (row: CharacterSummary) => (row.name || '?').trim().charAt(0)
const bioExcerpt = (row: CharacterSummary) => (row.bio || '还没有简介。').replace(/\s+/g, ' ').trim()
onMounted(load)
</script>
<template>
  <div>
    <StageHero variant="banner" :img="asset('banner-notes')" title="人物志" en="characters · portraits" line="用一张肖像和自定义信息，整理想记住的人物" />
    <div class="site-main">
      <div class="toolbar">
        <span class="hint">{{ rows.length }} 位人物</span>
        <t-button theme="primary" @click="startCreate">新增人物</t-button>
      </div>
      <t-loading :loading="loading" class="load-region">
        <p v-if="!rows.length" class="empty">还没有人物，先建立第一份人物志。</p>
        <div class="character-list">
          <button
            v-for="row in rows" :key="row.id"
            class="card character-card" type="button"
            @click="router.push(`/characters/${row.id}`)"
          >
            <div class="thumb">
              <img v-if="portrait(row)" :src="portrait(row)!.url" :alt="row.name" />
              <span v-else class="initial">{{ initial(row) }}</span>
            </div>
            <div class="copy">
              <div class="head">
                <h2>{{ row.name }}</h2>
                <span class="visibility">{{ row.visibility === 'private' ? '仅隐私小屋' : '公开展示' }}</span>
              </div>
              <p v-if="row.subtitle" class="subtitle">{{ row.subtitle }}</p>
              <p class="bio">{{ bioExcerpt(row) }}</p>
            </div>
          </button>
        </div>
      </t-loading>
      <div v-if="creating" class="editor card">
        <div class="editor-head"><h2>新增人物</h2><t-button variant="text" @click="creating = false">关闭</t-button></div>
        <div class="form-grid">
          <t-input v-model="form.name" label="姓名" />
          <t-input v-model="form.subtitle" label="副标题" />
          <t-select v-model="form.visibility" label="展示范围" :options="[{ label: '公开展示', value: 'public' }, { label: '仅隐私小屋', value: 'private' }]" />
        </div>
        <t-textarea v-model="form.bio" label="人物简介" :autosize="{ minRows: 4 }" />
        <div class="fields">
          <div class="section-label">自定义信息</div>
          <div v-for="(field, i) in form.fields" :key="i" class="field-row">
            <t-input v-model="field.label" placeholder="栏目名" />
            <t-input v-model="field.value" placeholder="内容" />
            <t-button variant="text" @click="form.fields.splice(i, 1)">移除</t-button>
          </div>
          <t-button variant="outline" @click="form.fields.push({ label: '', value: '' })">添加栏目</t-button>
        </div>
        <div class="editor-actions"><t-button theme="primary" :loading="saving" @click="save">保存人物</t-button></div>
      </div>
    </div>
  </div>
</template>
<style scoped>
.toolbar, .editor-head, .editor-actions, .head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.toolbar { margin-bottom: 20px; }
.hint, .empty, .copy .bio, .subtitle { color: var(--ink-soft); }
.load-region { min-height: 240px; display: block; }
.empty { padding: 36px 0; }
.character-list { display: grid; gap: 16px; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }
.character-card {
  display: flex; gap: 16px; align-items: flex-start; padding: 16px 18px;
  text-align: left; font: inherit; cursor: pointer;
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}
.character-card:hover {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--sea-mid) 55%, var(--card-line));
  box-shadow: 0 16px 34px -16px rgba(20, 90, 140, 0.32);
}
.thumb {
  width: 72px; height: 96px; flex: 0 0 72px; overflow: hidden; border-radius: 8px;
  background: var(--cloud); display: grid; place-items: center;
}
.thumb img { width: 100%; height: 100%; object-fit: cover; }
.thumb .initial { font-family: var(--font-display); font-size: 30px; color: var(--ink-soft); }
.copy { min-width: 0; flex: 1; }
.copy h2 { margin: 2px 0 0; font: 400 21px var(--font-display); letter-spacing: 0.04em; }
.subtitle { margin: 3px 0 0; font-size: 12.5px; }
.bio {
  margin: 8px 0 0; font-size: 13.5px; line-height: 1.7;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.visibility { font-size: 12px; color: var(--brand); white-space: nowrap; }
.editor { position: fixed; z-index: 20; right: 24px; bottom: 24px; width: min(620px, calc(100vw - 32px)); max-height: calc(100vh - 48px); overflow: auto; padding: 22px; box-shadow: var(--shadow); }
.editor-head h2 { margin: 0; font-size: 20px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 18px 0; }
.fields { margin-top: 18px; }
.section-label { font-size: 14px; color: var(--ink-soft); margin-bottom: 8px; }
.field-row { display: grid; grid-template-columns: 1fr 2fr auto; gap: 8px; margin-bottom: 8px; }
.editor-actions { justify-content: flex-end; margin-top: 18px; }
@media (max-width: 640px) { .form-grid { grid-template-columns: 1fr; } .field-row { grid-template-columns: 1fr 1fr; } }
</style>
