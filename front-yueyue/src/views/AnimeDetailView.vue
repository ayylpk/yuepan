<script setup lang="ts">
// 动漫详情(10/19 从 AnimeView 拆出):/anime/:id,只渲染一部作品。
// 原列表页里"整块平铺"的内容(简介 / 图片总集 / 分季与集数)原样搬到这里。
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http, postForm } from '@/api/http'
import type { AnimeWork } from '@/api/types'
import ImageLightbox from '@/components/ImageLightbox.vue'
import { uploadImagesSequentially } from '@/utils/uploadImages'
import { getNextEpisodeNumber, getNextSeasonNumber, isValidPositiveInteger } from '@/utils/animeEntryForm'

const route = useRoute()
const router = useRouter()
const workId = computed(() => Number(route.params.id))

const work = ref<AnimeWork | null>(null)
const loading = ref(true)
const editing = ref(false)
const saving = ref(false)
const form = reactive({ title: '', subtitle: '', description: '', visibility: 'public' })
const selectedSeason = ref<number | null>(null)
const viewer = ref<{ url: string; name: string } | null>(null)
const uploading = ref<string | null>(null)
const entryDialog = ref<{ kind: 'season' | 'episode'; workId: number; seasonId?: number; context: string } | null>(null)
const entryForm = reactive({ number: 1, title: '' })
const savingEntry = ref(false)
const entryVisible = computed({
  get: () => entryDialog.value !== null,
  set: visible => { if (!visible && !savingEntry.value) entryDialog.value = null },
})

async function load() {
  loading.value = true
  try {
    work.value = await http.get<AnimeWork>(`/api/anime/${workId.value}`)
    Object.assign(form, {
      title: work.value.title, subtitle: work.value.subtitle,
      description: work.value.description, visibility: work.value.visibility,
    })
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '加载失败')
    router.replace('/anime')
  } finally {
    loading.value = false
  }
}
async function save() {
  if (!form.title.trim()) return MessagePlugin.warning('请填写作品名称')
  saving.value = true
  try {
    await http.put(`/api/anime/${workId.value}`, { ...form })
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
  if (!confirm('删除作品以及它的季、集和图片？')) return
  try {
    await http.del(`/api/anime/${workId.value}`)
    MessagePlugin.success('已删除')
    router.replace('/anime')
  } catch (e) {
    // 删除失败要说出来,不能静默(旧写法是裸 await,失败时界面毫无反应)
    MessagePlugin.error(e instanceof ApiError ? e.message : '删除失败')
  }
}
function startAddSeason() {
  if (!work.value) return
  entryDialog.value = { kind: 'season', workId: work.value.id, context: work.value.title }
  Object.assign(entryForm, { number: getNextSeasonNumber(work.value.seasons), title: '' })
}
function startAddEpisode(season: AnimeWork['seasons'][number]) {
  if (!work.value) return
  entryDialog.value = { kind: 'episode', workId: work.value.id, seasonId: season.id, context: `${work.value.title} · 第${season.season_number}季` }
  Object.assign(entryForm, { number: getNextEpisodeNumber(season.episodes), title: '' })
}
async function saveEntry() {
  const dialog = entryDialog.value
  if (!dialog) return
  if (!isValidPositiveInteger(entryForm.number)) return MessagePlugin.warning(dialog.kind === 'season' ? '季数需要是正整数' : '集数需要是正整数')
  savingEntry.value = true
  try {
    if (dialog.kind === 'season') {
      await http.post(`/api/anime/${dialog.workId}/seasons`, { season_number: entryForm.number, title: entryForm.title.trim() })
    } else {
      await http.post(`/api/anime/seasons/${dialog.seasonId}/episodes`, { episode_number: entryForm.number, title: entryForm.title.trim(), feeling: '' })
      selectedSeason.value = dialog.seasonId ?? null
    }
    entryDialog.value = null
    MessagePlugin.success(dialog.kind === 'season' ? '已新增一季' : '已新增一集')
    await load()
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '保存失败，请重试')
  } finally {
    savingEntry.value = false
  }
}
async function updateFeeling(episodeId: number, episode_number: number, title: string, feeling: string) {
  // 失焦即存:失败必须提示,否则用户以为写进去了(旧写法是裸 await,失败静默丢内容)
  try {
    await http.put(`/api/anime/episodes/${episodeId}`, { episode_number, title, feeling })
    await load()
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '感想没存上，请重试')
  }
}
async function upload(event: Event, episode_id?: number) {
  if (!work.value) return
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  if (!files.length) return
  const key = `${work.value.id}:${episode_id ?? 'all'}`
  uploading.value = key
  const result = await uploadImagesSequentially(files, async file => {
    const fd = new FormData()
    fd.append('file', file)
    if (episode_id) fd.append('episode_id', String(episode_id))
    await postForm(`/api/anime/${work.value!.id}/images`, fd)
  })
  uploading.value = null
  if (result.succeeded.length) await load()
  if (result.failed.length) MessagePlugin.warning(`已上传 ${result.succeeded.length} 张，${result.failed.length} 张失败`)
  else MessagePlugin.success(episode_id ? `已加入本集和总图集：${result.succeeded.length} 张` : `已加入总图集：${result.succeeded.length} 张`)
}
const openImage = (url: string, name: string) => { viewer.value = { url, name } }
onMounted(load)
watch(() => route.params.id, load)
</script>
<template>
  <div class="site-main detail-page">
    <t-loading :loading="loading">
      <template v-if="work">
        <div class="detail-top">
          <header class="page-head">
            <h2>{{ work.title }}</h2>
            <p class="meta">
              <span v-if="work.subtitle">{{ work.subtitle }}</span>
              <span>{{ work.images.length }} 图</span>
              <span>{{ work.seasons.length }} 季</span>
              <span v-if="work.updated_at">{{ work.updated_at.slice(0, 16) }}</span>
              <span class="tag">{{ work.visibility === 'private' ? '仅隐私小屋' : '公开展示' }}</span>
            </p>
          </header>
          <div class="actions">
            <t-button theme="primary" variant="outline" @click="editing = true">编辑简介</t-button>
            <t-button theme="danger" variant="text" @click="remove">删除作品</t-button>
            <t-button variant="text" @click="router.push('/anime')">回列表</t-button>
          </div>
        </div>

        <p class="description">{{ work.description || '暂无简介' }}</p>

        <section class="collection">
          <div class="section-head">
            <h3>图片总集 <small>{{ work.images.length }}</small></h3>
            <label class="upload">{{ uploading === `${work.id}:all` ? '上传中…' : '批量上传图片' }}<input type="file" accept="image/*" multiple :disabled="uploading === `${work.id}:all`" @change="upload($event)" /></label>
          </div>
          <div class="gallery">
            <button v-for="image in work.images" :key="image.id" class="image-thumb" type="button" :aria-label="`放大图片：${image.name}`" @click="openImage(image.url, image.name)"><img :src="image.url" :alt="image.name" /></button>
            <p v-if="!work.images.length" class="hint">还没有图片。</p>
          </div>
        </section>

        <section class="seasons">
          <div class="section-head"><h3>分季与集数</h3><t-button size="small" variant="outline" @click="startAddSeason">新增一季</t-button></div>
          <div v-for="season in work.seasons" :key="season.id" class="season">
            <button class="season-toggle" @click="selectedSeason = selectedSeason === season.id ? null : season.id">
              <span>第{{ season.season_number }}季<span v-if="season.title"> · {{ season.title }}</span></span>
              <span>{{ selectedSeason === season.id ? '−' : '+' }}</span>
            </button>
            <div v-if="selectedSeason === season.id" class="episodes">
              <div class="episode-tools"><t-button size="small" @click="startAddEpisode(season)">新增一集</t-button></div>
              <article v-for="episode in season.episodes" :key="episode.id" class="episode">
                <div class="episode-title">第{{ episode.episode_number }}集<span v-if="episode.title"> · {{ episode.title }}</span></div>
                <t-textarea v-model="episode.feeling" placeholder="写下这一集的感想" :autosize="{ minRows: 2, maxRows: 8 }" @blur="updateFeeling(episode.id, episode.episode_number, episode.title, episode.feeling)" />
                <div class="episode-gallery">
                  <button v-for="image in work.images.filter(i => i.episode_id === episode.id)" :key="image.id" class="image-thumb" type="button" :aria-label="`放大图片：${image.name}`" @click="openImage(image.url, image.name)"><img :src="image.url" :alt="image.name" /></button>
                  <label class="upload small">{{ uploading === `${work.id}:${episode.id}` ? '上传中…' : '+ 本集图片' }}<input type="file" accept="image/*" multiple :disabled="uploading === `${work.id}:${episode.id}`" @change="upload($event, episode.id)" /></label>
                </div>
              </article>
              <p v-if="!season.episodes.length" class="hint">本季还没有集数。</p>
            </div>
          </div>
          <p v-if="!work.seasons.length" class="hint">先添加一季，再添加集数。</p>
        </section>

        <div v-if="editing" class="editor card">
          <div class="editor-head"><h2>编辑作品</h2><t-button variant="text" @click="editing = false">关闭</t-button></div>
          <div class="form-grid">
            <t-input v-model="form.title" label="作品名称" />
            <t-input v-model="form.subtitle" label="副标题" />
            <t-select v-model="form.visibility" label="展示范围" :options="[{ label: '公开展示', value: 'public' }, { label: '仅隐私小屋', value: 'private' }]" />
          </div>
          <t-textarea v-model="form.description" label="作品简介" :autosize="{ minRows: 5 }" />
          <div class="editor-actions"><t-button theme="primary" :loading="saving" @click="save">保存作品</t-button></div>
        </div>

        <t-dialog v-model:visible="entryVisible" :header="entryDialog?.kind === 'season' ? '新增一季' : '新增一集'" :confirm-btn="{ content: '保存', loading: savingEntry }" cancel-btn="取消" @confirm="saveEntry" @cancel="entryDialog = null">
          <div v-if="entryDialog" class="entry-form">
            <div class="entry-context"><span class="entry-mark">{{ entryDialog.kind === 'season' ? '季' : '集' }}</span><div><strong>{{ entryDialog.kind === 'season' ? '整理新的篇章' : '记录这一集' }}</strong><span>{{ entryDialog.context }}</span></div></div>
            <div class="entry-field"><label>{{ entryDialog.kind === 'season' ? '季数' : '集数' }}</label><t-input-number v-model="entryForm.number" :min="1" :step="1" theme="normal" /></div>
            <div class="entry-field"><label>{{ entryDialog.kind === 'season' ? '季标题' : '集标题' }} <span>选填</span></label><t-input v-model="entryForm.title" :placeholder="entryDialog.kind === 'season' ? '例如：特别篇' : '为这一集添加一个标题'" maxlength="80" /></div>
            <p class="entry-hint">{{ entryDialog.kind === 'season' ? '季数已按现有内容自动接续，也可以自行调整。' : '集数已按本季内容自动接续，也可以自行调整。' }}</p>
          </div>
        </t-dialog>
        <ImageLightbox v-if="viewer" :src="viewer.url" :alt="viewer.name" :caption="viewer.name" @close="viewer = null" />
      </template>
    </t-loading>
  </div>
</template>
<style scoped>
.detail-page { padding-top: 32px; }
.detail-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
.detail-top .page-head { margin-bottom: 0; }
.meta { margin: 8px 0 0; display: flex; gap: 12px; flex-wrap: wrap; font-size: 13px; color: var(--ink-soft); }
.tag { color: var(--brand); }
.actions { display: flex; gap: 6px; flex-wrap: wrap; }
.description { margin: 0 0 8px; line-height: 1.8; white-space: pre-wrap; max-width: 74ch; }
.section-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
.section-head h3 { margin: 0; font-size: 16px; }
.section-head small { color: var(--ink-soft); font-weight: 400; }
.collection, .seasons { margin-top: 26px; }
.upload { padding: 7px 11px; border: 1px solid var(--line); border-radius: 7px; color: var(--brand); cursor: pointer; font-size: 13px; }
.upload input { display: none; }
.gallery, .episode-gallery { display: flex; gap: 9px; flex-wrap: wrap; }
.gallery .hint, .seasons .hint { color: var(--ink-soft); font-size: 13px; }
.image-thumb { width: 112px; height: 84px; padding: 0; overflow: hidden; border: 1px solid var(--line); border-radius: 7px; background: none; cursor: zoom-in; }
.image-thumb img { display: block; width: 100%; height: 100%; object-fit: cover; }
.season { border-top: 1px solid var(--line); }
.season-toggle { width: 100%; display: flex; justify-content: space-between; padding: 14px 4px; border: 0; background: none; color: var(--ink); font: inherit; text-align: left; cursor: pointer; }
.episodes { padding: 0 8px 16px; }
.episode-tools { display: flex; justify-content: flex-end; margin-bottom: 10px; }
.episode { padding: 12px 0; border-top: 1px solid var(--line); }
.episode-title { font-size: 14px; font-weight: 600; margin-bottom: 9px; }
.episode-gallery { margin-top: 9px; }
.upload.small { width: 112px; height: 84px; display: grid; place-items: center; }
.editor { position: fixed; z-index: 20; right: 24px; bottom: 24px; width: min(620px, calc(100vw - 32px)); max-height: calc(100vh - 48px); overflow: auto; padding: 22px; box-shadow: var(--shadow); }
.editor-head, .editor-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.editor-head h2 { margin: 0; font-size: 20px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 18px 0; }
.editor-actions { justify-content: flex-end; margin-top: 18px; }
.entry-form { padding: 4px 2px 0; }
.entry-context { display: flex; align-items: center; gap: 13px; padding: 14px; border: 1px solid var(--line); border-radius: 8px; background: color-mix(in srgb, var(--cloud) 32%, var(--card)); }
.entry-mark { display: grid; width: 42px; height: 42px; flex: 0 0 42px; place-items: center; border-radius: 8px; background: var(--brand); color: #fff; font-family: var(--font-display); font-size: 21px; }
.entry-context strong, .entry-context span:not(.entry-mark) { display: block; }
.entry-context strong { color: var(--ink); font-size: 14px; font-weight: 600; }
.entry-context div span { margin-top: 3px; color: var(--ink-soft); font-size: 12px; }
.entry-field { display: grid; gap: 7px; margin-top: 18px; }
.entry-field label { color: var(--ink); font-size: 13px; font-weight: 600; }
.entry-field label span { margin-left: 5px; color: var(--ink-soft); font-weight: 400; }
.entry-field :deep(.t-input-number), .entry-field :deep(.t-input) { width: 100%; }
.entry-hint { margin: 12px 0 0; color: var(--ink-soft); font-size: 12px; line-height: 1.6; }
@media (max-width: 640px) {
  .form-grid { grid-template-columns: 1fr; }
  .image-thumb, .upload.small { width: calc((100vw - 86px) / 3); height: 80px; }
}
</style>
