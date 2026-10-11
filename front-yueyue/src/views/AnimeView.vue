<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http, postForm } from '@/api/http'
import type { AnimeWork } from '@/api/types'
import StageHero from '@/components/StageHero.vue'
import { asset } from '@/stores/season'

const works = ref<AnimeWork[]>([])
const active = ref<AnimeWork | null>(null)
const creating = ref(false)
const form = reactive({ title: '', subtitle: '', description: '', visibility: 'public' })
const selectedSeason = ref<number | null>(null)
async function load() { try { works.value = await http.get<AnimeWork[]>('/api/anime') } catch (e) { MessagePlugin.error(e instanceof Error ? e.message : '加载失败') } }
function startCreate() { active.value = null; Object.assign(form, { title: '', subtitle: '', description: '', visibility: 'public' }); creating.value = true }
function edit(work: AnimeWork) { active.value = work; Object.assign(form, { title: work.title, subtitle: work.subtitle, description: work.description, visibility: work.visibility }); creating.value = true }
async function save() { if (!form.title.trim()) return MessagePlugin.warning('请填写作品名称'); try { const payload = { ...form }; if (active.value) await http.put(`/api/anime/${active.value.id}`, payload); else await http.post('/api/anime', payload); creating.value = false; MessagePlugin.success('已保存'); await load() } catch (e) { MessagePlugin.error(e instanceof ApiError ? e.message : '保存失败') } }
async function addSeason(work: AnimeWork) { const title = prompt('季标题（可留空）', `第${work.seasons.length + 1}季`); if (title === null) return; await http.post(`/api/anime/${work.id}/seasons`, { season_number: work.seasons.length + 1, title }); await load() }
async function addEpisode(seasonId: number) { const title = prompt('集标题'); if (title === null) return; const episode_number = Number(prompt('集数', '1')); if (!Number.isInteger(episode_number) || episode_number < 1) return MessagePlugin.warning('集数需要是正整数'); await http.post(`/api/anime/seasons/${seasonId}/episodes`, { episode_number, title, feeling: '' }); await load() }
async function updateFeeling(episodeId: number, episode_number: number, title: string, feeling: string) { await http.put(`/api/anime/episodes/${episodeId}`, { episode_number, title, feeling }); await load() }
async function upload(work: AnimeWork, file?: File, episode_id?: number) { if (!file) return; const fd = new FormData(); fd.append('file', file); if (episode_id) fd.append('episode_id', String(episode_id)); try { await postForm(`/api/anime/${work.id}/images`, fd); MessagePlugin.success('图片已加入总图集'); await load() } catch (e) { MessagePlugin.error(e instanceof Error ? e.message : '上传失败') } }
async function remove(work: AnimeWork) { if (!confirm('删除作品以及它的季、集和图片？')) return; await http.del(`/api/anime/${work.id}`); await load() }
onMounted(load)
</script>
<template>
  <div><StageHero variant="banner" :img="asset('banner-notes')" title="动漫收藏" en="anime · scenes & stories" line="每部作品独立整理，按季、按集留下画面和感想" />
    <div class="site-main"><div class="toolbar"><span class="hint">{{ works.length }} 部作品</span><t-button theme="primary" @click="startCreate">新增作品</t-button></div>
      <p v-if="!works.length" class="empty">还没有作品，添加一部开始整理。</p>
      <article v-for="work in works" :key="work.id" class="work card">
        <header class="work-head"><div><span class="visibility">{{ work.visibility === 'private' ? '仅隐私小屋' : '公开展示' }}</span><h2>{{ work.title }}</h2><p>{{ work.subtitle }}</p></div><div class="actions"><t-button variant="outline" @click="edit(work)">编辑简介</t-button><t-button variant="text" theme="danger" @click="remove(work)">删除作品</t-button></div></header>
        <p class="description">{{ work.description || '暂无简介' }}</p>
        <section class="collection"><div class="section-head"><h3>图片总集 <small>{{ work.images.length }}</small></h3><label class="upload">上传总集图片<input type="file" accept="image/*" @change="upload(work, ($event.target as HTMLInputElement).files?.[0])" /></label></div><div class="gallery"><img v-for="image in work.images" :key="image.id" :src="image.url" :alt="image.name" /></div></section>
        <section class="seasons"><div class="section-head"><h3>分季与集数</h3><t-button size="small" variant="outline" @click="addSeason(work)">新增一季</t-button></div>
          <div v-for="season in work.seasons" :key="season.id" class="season"><button class="season-toggle" @click="selectedSeason = selectedSeason === season.id ? null : season.id"><span>第{{ season.season_number }}季<span v-if="season.title"> · {{ season.title }}</span></span><span>{{ selectedSeason === season.id ? '−' : '+' }}</span></button>
            <div v-if="selectedSeason === season.id" class="episodes"><div class="episode-tools"><t-button size="small" @click="addEpisode(season.id)">新增一集</t-button></div><article v-for="episode in season.episodes" :key="episode.id" class="episode"><div class="episode-title">第{{ episode.episode_number }}集<span v-if="episode.title"> · {{ episode.title }}</span></div><t-textarea v-model="episode.feeling" placeholder="写下这一集的感想" :autosize="{ minRows: 2, maxRows: 8 }" @blur="updateFeeling(episode.id, episode.episode_number, episode.title, episode.feeling)" /><div class="episode-gallery"><img v-for="image in work.images.filter(i => i.episode_id === episode.id)" :key="image.id" :src="image.url" :alt="image.name" /><label class="upload small">+ 本集图片<input type="file" accept="image/*" @change="upload(work, ($event.target as HTMLInputElement).files?.[0], episode.id)" /></label></div></article><p v-if="!season.episodes.length" class="hint">本季还没有集数。</p></div>
          </div><p v-if="!work.seasons.length" class="hint">先添加一季，再添加集数。</p>
        </section>
      </article>
      <div v-if="creating" class="editor card"><div class="editor-head"><h2>{{ active ? '编辑作品' : '新增作品' }}</h2><t-button variant="text" @click="creating = false">关闭</t-button></div><div class="form-grid"><t-input v-model="form.title" label="作品名称" /><t-input v-model="form.subtitle" label="副标题" /><t-select v-model="form.visibility" label="展示范围" :options="[{label:'公开展示',value:'public'},{label:'仅隐私小屋',value:'private'}]" /></div><t-textarea v-model="form.description" label="作品简介" :autosize="{ minRows: 5 }" /><div class="editor-actions"><t-button theme="primary" @click="save">保存作品</t-button></div></div>
    </div>
  </div>
</template>
<style scoped>
.toolbar,.work-head,.actions,.section-head,.editor-head,.editor-actions{display:flex;align-items:center;justify-content:space-between;gap:12px}.toolbar{margin-bottom:20px}.hint,.work-head p,.description{color:var(--ink-soft)}.work{padding:22px;margin-bottom:20px}.work-head h2{margin:6px 0 3px;font:400 27px var(--font-display)}.work-head p{margin:0}.visibility{font-size:12px;color:var(--brand)}.description{line-height:1.75;white-space:pre-wrap}.collection,.seasons{margin-top:24px}.section-head{margin-bottom:10px}.section-head h3{margin:0;font-size:16px}.section-head small{color:var(--ink-soft);font-weight:400}.upload{padding:7px 11px;border:1px solid var(--line);border-radius:7px;color:var(--brand);cursor:pointer;font-size:13px}.upload input{display:none}.gallery,.episode-gallery{display:flex;gap:9px;flex-wrap:wrap}.gallery img,.episode-gallery img{width:112px;height:84px;border-radius:7px;object-fit:cover}.season{border-top:1px solid var(--line)}.season-toggle{width:100%;display:flex;justify-content:space-between;padding:14px 4px;border:0;background:none;color:var(--ink);font:inherit;text-align:left;cursor:pointer}.episodes{padding:0 8px 16px}.episode-tools{display:flex;justify-content:flex-end;margin-bottom:10px}.episode{padding:12px 0;border-top:1px solid var(--line)}.episode-title{font-size:14px;font-weight:600;margin-bottom:9px}.episode-gallery{margin-top:9px}.upload.small{width:112px;height:84px;display:grid;place-items:center}.editor{position:fixed;z-index:20;right:24px;bottom:24px;width:min(620px,calc(100vw - 32px));max-height:calc(100vh - 48px);overflow:auto;padding:22px;box-shadow:var(--shadow)}.editor-head h2{margin:0;font-size:20px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:18px 0}.editor-actions{justify-content:flex-end;margin-top:18px}.empty{padding:36px 0}@media(max-width:640px){.work-head{align-items:flex-start;flex-direction:column}.actions{flex-wrap:wrap}.form-grid{grid-template-columns:1fr}.gallery img,.episode-gallery img{width:calc((100vw - 86px)/3);height:80px}}
</style>
