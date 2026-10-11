<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http, postForm } from '@/api/http'
import type { CharacterProfile } from '@/api/types'
import StageHero from '@/components/StageHero.vue'
import { asset } from '@/stores/season'

const rows = ref<CharacterProfile[]>([])
const loading = ref(true)
const editing = ref(false)
const active = ref<CharacterProfile | null>(null)
const form = reactive({ name: '', subtitle: '', bio: '', visibility: 'public', fields: [{ label: '身高', value: '' }, { label: '体重', value: '' }, { label: '出自', value: '' }, { label: '爱好', value: '' }] })
async function load() { loading.value = true; try { rows.value = await http.get<CharacterProfile[]>('/api/characters') } catch (e) { MessagePlugin.error(e instanceof Error ? e.message : '加载失败') } finally { loading.value = false } }
function start(row?: CharacterProfile) { active.value = row || null; editing.value = true; Object.assign(form, row ? { name: row.name, subtitle: row.subtitle, bio: row.bio, visibility: row.visibility, fields: row.fields.map(f => ({ label: f.label, value: f.value })) } : { name: '', subtitle: '', bio: '', visibility: 'public', fields: [{ label: '身高', value: '' }, { label: '体重', value: '' }, { label: '出自', value: '' }, { label: '爱好', value: '' }] }) }
async function save() { if (!form.name.trim()) return MessagePlugin.warning('请填写人物名称'); try { const payload = { ...form, fields: form.fields.filter(f => f.label.trim()) }; if (active.value) await http.put(`/api/characters/${active.value.id}`, payload); else await http.post('/api/characters', payload); MessagePlugin.success('已保存'); editing.value = false; await load() } catch (e) { MessagePlugin.error(e instanceof ApiError ? e.message : '保存失败') } }
async function upload(row: CharacterProfile, file?: File) { if (!file) return; const fd = new FormData(); fd.append('file', file); try { await postForm(`/api/characters/${row.id}/images`, fd); MessagePlugin.success('图片已加入'); await load() } catch (e) { MessagePlugin.error(e instanceof Error ? e.message : '上传失败') } }
async function remove(row: CharacterProfile) { if (!confirm('删除这个人物及其图片？')) return; await http.del(`/api/characters/${row.id}`); await load() }
onMounted(load)
</script>
<template>
  <div><StageHero variant="banner" :img="asset('banner-notes')" title="人物志" en="characters · portraits" line="用图片和自定义信息，整理想记住的人物" />
    <div class="site-main">
      <div class="toolbar"><span class="hint">{{ rows.length }} 位人物</span><t-button theme="primary" @click="start()">新增人物</t-button></div>
      <p v-if="loading">加载中…</p><p v-else-if="!rows.length" class="empty">还没有人物，先建立第一份人物志。</p>
      <div class="character-grid">
        <article v-for="row in rows" :key="row.id" class="card character-card">
          <div class="character-layout"><div class="portrait-placeholder"><img v-if="row.images[0]" :src="row.images[0].url" :alt="row.name" /><span v-else>portrait</span></div><div class="character-copy"><div class="card-head"><div><h2>{{ row.name }}</h2><p>{{ row.subtitle }}</p></div><span class="visibility">{{ row.visibility === 'private' ? '仅隐私小屋' : '公开展示' }}</span></div><p class="bio">{{ row.bio || '还没有简介。' }}</p><dl><template v-for="field in row.fields" :key="field.id || field.label"><dt>{{ field.label }}</dt><dd>{{ field.value || '—' }}</dd></template></dl></div></div>
          <div class="gallery"><img v-for="image in row.images" :key="image.id" :src="image.url" :alt="image.name" /><label class="upload">+ 图片<input type="file" accept="image/*" @change="upload(row, ($event.target as HTMLInputElement).files?.[0])" /></label></div>
          <div class="card-actions"><t-button variant="text" @click="start(row)">编辑</t-button><t-button variant="text" theme="danger" @click="remove(row)">删除</t-button></div>
        </article>
      </div>
      <div v-if="editing" class="editor card"><div class="editor-head"><h2>{{ active ? '编辑人物' : '新增人物' }}</h2><t-button variant="text" @click="editing = false">关闭</t-button></div><div class="form-grid"><t-input v-model="form.name" label="姓名" /><t-input v-model="form.subtitle" label="副标题" /><t-select v-model="form.visibility" label="展示范围" :options="[{label:'公开展示',value:'public'},{label:'仅隐私小屋',value:'private'}]" /></div><t-textarea v-model="form.bio" label="人物简介" :autosize="{ minRows: 4 }" /><div class="fields"><div class="section-label">自定义信息</div><div v-for="(field, i) in form.fields" :key="i" class="field-row"><t-input v-model="field.label" placeholder="栏目名" /><t-input v-model="field.value" placeholder="内容" /><t-button variant="text" @click="form.fields.splice(i, 1)">移除</t-button></div><t-button variant="outline" @click="form.fields.push({ label: '', value: '' })">添加栏目</t-button></div><div class="editor-actions"><t-button theme="primary" @click="save">保存人物</t-button></div></div>
    </div>
  </div>
</template>
<style scoped>
.toolbar,.card-head,.editor-head,.editor-actions,.card-actions{display:flex;align-items:center;justify-content:space-between;gap:12px}.toolbar{margin-bottom:20px}.hint,.character-copy p,.empty{color:var(--ink-soft)}.character-grid{display:grid;gap:18px}.character-card{padding:20px}.character-layout{display:grid;grid-template-columns:180px 1fr;gap:24px}.portrait-placeholder{aspect-ratio:3/4;background:var(--cloud);border-radius:10px;display:grid;place-items:center;color:var(--ink-soft);overflow:hidden}.portrait-placeholder img{width:100%;height:100%;object-fit:cover}.card-head h2{margin:0;font-family:var(--font-display);font-weight:400}.card-head p{margin:5px 0}.visibility{font-size:12px;color:var(--brand);white-space:nowrap}.bio{line-height:1.7}.character-copy dl{display:grid;grid-template-columns:max-content 1fr;gap:8px 18px;margin:16px 0 0;font-size:14px}.character-copy dt{color:var(--ink-soft)}.character-copy dd{margin:0}.gallery{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px}.gallery img,.upload{width:74px;height:74px;border-radius:8px;object-fit:cover;border:1px solid var(--line)}.upload{display:grid;place-items:center;color:var(--brand);cursor:pointer;font-size:12px}.upload input{display:none}.card-actions{justify-content:flex-end;margin-top:8px}.editor{position:fixed;z-index:20;right:24px;bottom:24px;width:min(620px,calc(100vw - 32px));max-height:calc(100vh - 48px);overflow:auto;padding:22px;box-shadow:var(--shadow)}.editor-head h2{margin:0;font-size:20px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:18px 0}.fields{margin-top:18px}.section-label{font-size:14px;color:var(--ink-soft);margin-bottom:8px}.field-row{display:grid;grid-template-columns:1fr 2fr auto;gap:8px;margin-bottom:8px}.editor-actions{justify-content:flex-end;margin-top:18px}@media(max-width:640px){.character-layout{grid-template-columns:100px 1fr;gap:14px}.form-grid{grid-template-columns:1fr}.field-row{grid-template-columns:1fr 1fr}.field-row .t-button{grid-column:span 2;justify-self:end}}
</style>
