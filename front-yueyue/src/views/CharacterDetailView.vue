<script setup lang="ts">
// 人物志详情(10/19 从 CharactersView 拆出):/characters/:id。
// 左侧 = 独立肖像位(读 cover_image_id,不是图集第一张);下方 = 批量图片。
// A 方案:空槽位点击直接选图上传,接口 POST /api/characters/{id}/portrait 会把它置为封面。
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http, postForm } from '@/api/http'
import type { CharacterProfile } from '@/api/types'
import ImageLightbox from '@/components/ImageLightbox.vue'
import { uploadImagesSequentially } from '@/utils/uploadImages'

const route = useRoute()
const router = useRouter()
const characterId = computed(() => Number(route.params.id))

const row = ref<CharacterProfile | null>(null)
const loading = ref(true)
const editing = ref(false)
const saving = ref(false)
const viewer = ref<{ url: string; name: string } | null>(null)
const uploadingBatch = ref(false)
const uploadingPortrait = ref(false)
const portraitInput = ref<HTMLInputElement | null>(null)
const form = reactive({
  name: '', subtitle: '', bio: '', visibility: 'public',
  fields: [{ label: '', value: '' }] as { label: string; value: string }[],
})

const portrait = computed(() => row.value?.images.find(i => i.id === row.value?.cover_image_id) ?? null)
const gallery = computed(() => row.value?.images.filter(i => i.id !== row.value?.cover_image_id) ?? [])

async function load() {
  loading.value = true
  try {
    row.value = await http.get<CharacterProfile>(`/api/characters/${characterId.value}`)
    Object.assign(form, {
      name: row.value.name, subtitle: row.value.subtitle, bio: row.value.bio,
      visibility: row.value.visibility,
      fields: row.value.fields.map(f => ({ label: f.label, value: f.value })),
    })
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '加载失败')
    router.replace('/characters')
  } finally {
    loading.value = false
  }
}
async function save() {
  if (!form.name.trim()) return MessagePlugin.warning('请填写人物名称')
  saving.value = true
  try {
    await http.put(`/api/characters/${characterId.value}`, {
      ...form, fields: form.fields.filter(f => f.label.trim()),
    })
    MessagePlugin.success('已保存')
    editing.value = false
    await load()
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}
async function remove() {
  if (!confirm('删除这个人物及其图片？')) return
  try {
    await http.del(`/api/characters/${characterId.value}`)
    MessagePlugin.success('已删除')
    router.replace('/characters')
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '删除失败')
  }
}
function onPortraitClick() {
  if (portrait.value) viewer.value = { url: portrait.value.url, name: portrait.value.name }
  else portraitInput.value?.click()
}
async function uploadPortrait(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  uploadingPortrait.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    await postForm(`/api/characters/${characterId.value}/portrait`, fd)
    MessagePlugin.success('肖像已更新')
    await load()
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '肖像上传失败')
  } finally {
    uploadingPortrait.value = false
  }
}
async function uploadBatch(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  if (!files.length) return
  uploadingBatch.value = true
  const result = await uploadImagesSequentially(files, async file => {
    const fd = new FormData()
    fd.append('file', file)
    await postForm(`/api/characters/${characterId.value}/images`, fd)
  })
  uploadingBatch.value = false
  if (result.succeeded.length) await load()
  if (result.failed.length) MessagePlugin.warning(`已上传 ${result.succeeded.length} 张，${result.failed.length} 张失败`)
  else MessagePlugin.success(`已加入 ${result.succeeded.length} 张图片`)
}
const openImage = (url: string, name: string) => { viewer.value = { url, name } }
onMounted(load)
watch(() => route.params.id, load)
</script>
<template>
  <div class="site-main detail-page">
    <t-loading :loading="loading">
      <template v-if="row">
        <div class="detail-top">
          <header class="page-head">
            <h2>{{ row.name }}</h2>
            <p class="meta">
              <span v-if="row.subtitle">{{ row.subtitle }}</span>
              <span v-if="row.updated_at">{{ row.updated_at.slice(0, 16) }}</span>
              <span class="tag">{{ row.visibility === 'private' ? '仅隐私小屋' : '公开展示' }}</span>
            </p>
          </header>
          <div class="actions">
            <t-button theme="primary" variant="outline" @click="editing = true">编辑资料</t-button>
            <t-button theme="danger" variant="text" @click="remove">删除人物</t-button>
            <t-button variant="text" @click="router.push('/characters')">回列表</t-button>
          </div>
        </div>

        <div class="character-layout">
          <div class="portrait-col">
            <button class="portrait" type="button" :class="{ empty: !portrait }" :aria-label="portrait ? '放大肖像' : '上传肖像'" @click="onPortraitClick">
              <img v-if="portrait" :src="portrait.url" :alt="row.name" />
              <span v-else class="portrait-empty">
                <span class="plus">＋</span>
                <span>{{ uploadingPortrait ? '上传中…' : '上传肖像' }}</span>
              </span>
            </button>
            <input ref="portraitInput" class="sr-input" type="file" accept="image/*" @change="uploadPortrait" />
            <t-button v-if="portrait" variant="text" size="small" :loading="uploadingPortrait" @click="portraitInput?.click()">更换肖像</t-button>
            <p v-else class="portrait-hint">这一格是独立肖像，不占下方图集</p>
          </div>

          <div class="copy">
            <p class="bio">{{ row.bio || '还没有简介。' }}</p>
            <dl class="fields">
              <template v-for="field in row.fields" :key="field.id || field.label">
                <dt>{{ field.label }}</dt>
                <dd>{{ field.value || '—' }}</dd>
              </template>
            </dl>
          </div>
        </div>

        <section class="gallery-section">
          <div class="section-head">
            <h3>批量图片 <small>{{ gallery.length }}</small></h3>
            <label class="upload">{{ uploadingBatch ? '上传中…' : '+ 批量上传' }}<input type="file" accept="image/*" multiple :disabled="uploadingBatch" @change="uploadBatch" /></label>
          </div>
          <div class="gallery">
            <button v-for="image in gallery" :key="image.id" class="image-thumb" type="button" :aria-label="`放大图片：${image.name}`" @click="openImage(image.url, image.name)"><img :src="image.url" :alt="image.name" /></button>
            <p v-if="!gallery.length" class="hint">还没有图片。</p>
          </div>
        </section>

        <div v-if="editing" class="editor card">
          <div class="editor-head"><h2>编辑人物</h2><t-button variant="text" @click="editing = false">关闭</t-button></div>
          <div class="form-grid">
            <t-input v-model="form.name" label="姓名" />
            <t-input v-model="form.subtitle" label="副标题" />
            <t-select v-model="form.visibility" label="展示范围" :options="[{ label: '公开展示', value: 'public' }, { label: '仅隐私小屋', value: 'private' }]" />
          </div>
          <t-textarea v-model="form.bio" label="人物简介" :autosize="{ minRows: 4 }" />
          <div class="fields-editor">
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

        <ImageLightbox v-if="viewer" :src="viewer.url" :alt="viewer.name" :caption="viewer.name" @close="viewer = null" />
      </template>
    </t-loading>
  </div>
</template>
<style scoped>
.detail-page { padding-top: 32px; }
.detail-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; margin-bottom: 22px; }
.detail-top .page-head { margin-bottom: 0; }
.meta { margin: 8px 0 0; display: flex; gap: 12px; flex-wrap: wrap; font-size: 13px; color: var(--ink-soft); }
.tag { color: var(--brand); }
.actions { display: flex; gap: 6px; flex-wrap: wrap; }
.character-layout { display: grid; grid-template-columns: 220px 1fr; gap: 30px; align-items: start; }
.portrait-col { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; }
.portrait {
  width: 100%; aspect-ratio: 3 / 4; padding: 0; overflow: hidden; cursor: zoom-in;
  border: 1px solid var(--card-line); border-radius: 12px; background: var(--cloud); display: block;
}
.portrait.empty { cursor: pointer; border-style: dashed; background: color-mix(in srgb, var(--cloud) 55%, var(--card)); }
.portrait img { display: block; width: 100%; height: 100%; object-fit: cover; }
.portrait-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; width: 100%; height: 100%; color: var(--ink-soft); font-size: 13px; }
.portrait-empty .plus { font-size: 26px; line-height: 1; color: var(--brand); }
.portrait-hint { margin: 6px 0 0; font-size: 12px; color: var(--ink-soft); line-height: 1.6; }
.sr-input { display: none; }
.copy { min-width: 0; }
.bio { margin: 0; line-height: 1.85; white-space: pre-wrap; max-width: 70ch; }
.fields { display: grid; grid-template-columns: max-content 1fr; gap: 10px 20px; margin: 20px 0 0; font-size: 14px; }
.fields dt { color: var(--ink-soft); }
.fields dd { margin: 0; }
.gallery-section { margin-top: 32px; }
.section-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.section-head h3 { margin: 0; font-size: 16px; }
.section-head small { color: var(--ink-soft); font-weight: 400; }
.upload { padding: 7px 11px; border: 1px solid var(--line); border-radius: 7px; color: var(--brand); cursor: pointer; font-size: 13px; }
.upload input { display: none; }
.gallery { display: flex; gap: 9px; flex-wrap: wrap; }
.gallery .hint { color: var(--ink-soft); font-size: 13px; }
.image-thumb { width: 112px; height: 84px; padding: 0; overflow: hidden; border: 1px solid var(--line); border-radius: 7px; background: none; cursor: zoom-in; }
.image-thumb img { display: block; width: 100%; height: 100%; object-fit: cover; }
.editor { position: fixed; z-index: 20; right: 24px; bottom: 24px; width: min(620px, calc(100vw - 32px)); max-height: calc(100vh - 48px); overflow: auto; padding: 22px; box-shadow: var(--shadow); }
.editor-head, .editor-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.editor-head h2 { margin: 0; font-size: 20px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 18px 0; }
.fields-editor { margin-top: 18px; }
.section-label { font-size: 14px; color: var(--ink-soft); margin-bottom: 8px; }
.field-row { display: grid; grid-template-columns: 1fr 2fr auto; gap: 8px; margin-bottom: 8px; }
.editor-actions { justify-content: flex-end; margin-top: 18px; }
@media (max-width: 720px) {
  .character-layout { grid-template-columns: 120px 1fr; gap: 16px; }
  .form-grid { grid-template-columns: 1fr; }
  .field-row { grid-template-columns: 1fr 1fr; }
}
</style>
