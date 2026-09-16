<script setup lang="ts">
// 视频墙:列表/上传/删除对接 /api/videos(后端待补,要点是 Range 流式接口)。
// 播放器直接 <video src=/api/videos/{id}/stream>,后端回 206 才能拖进度条。
import { onMounted, reactive, ref } from 'vue'
import { DialogPlugin, MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http, postForm } from '@/api/http'
import type { VideoEntry } from '@/api/types'
import { asset } from '@/stores/season'
import PageHero from '@/components/PageHero.vue'

const videos = ref<VideoEntry[]>([])
const error = ref('')
const loading = ref(true)

const upload = reactive({ open: false, file: null as File | null, title: '', private: false, busy: false })

function fmtSize(n: number) {
  if (n > 1 << 30) return (n / (1 << 30)).toFixed(2) + ' GB'
  if (n > 1 << 20) return (n / (1 << 20)).toFixed(1) + ' MB'
  return Math.round(n / 1024) + ' KB'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    videos.value = await http.get<VideoEntry[]>('/api/videos')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function doUpload() {
  if (!upload.file) {
    MessagePlugin.warning('先选一个视频文件')
    return
  }
  upload.busy = true
  const form = new FormData()
  form.append('file', upload.file)
  form.append('title', upload.title)
  form.append('private', String(upload.private))
  try {
    await postForm<VideoEntry>('/api/videos/upload', form)
    MessagePlugin.success('传好了')
    Object.assign(upload, { open: false, file: null, title: '', private: false })
    await load()
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '上传失败')
  } finally {
    upload.busy = false
  }
}

function confirmDelete(v: VideoEntry) {
  const dlg = DialogPlugin.confirm({
    header: '删掉这个视频?',
    body: `「${v.title}」(${fmtSize(v.size)}) 文件会一起删掉。`,
    theme: 'warning',
    onConfirm: async () => {
      await http.del(`/api/videos/${v.id}`)
      dlg.hide()
      await load()
    },
  })
}

function pickFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  upload.file = f
  if (!upload.title) upload.title = f.name.replace(/\.[^.]+$/, '')
}

onMounted(load)
</script>

<template>
  <div>
    <PageHero :img="asset('banner-videos')" eyebrow="VIDEOS" title="视频">
      <p class="hero-sub">自留片单 · 拖动进度条不卡的流式播放</p>
    </PageHero>

    <div class="site-main">
      <div class="toolbar">
        <p class="hint">{{ videos.length ? `${videos.length} 个在架上` : '' }}</p>
        <t-button theme="primary" @click="upload.open = true">传视频</t-button>
      </div>

      <t-loading :loading="loading">
        <p v-if="error" class="load-error">{{ error }} —— /api/videos 还没实现,后端补的时候记得 Range 206</p>
        <div v-else-if="videos.length" class="vid-grid">
          <div v-for="v in videos" :key="v.id" class="glass-card vid-card">
            <video :src="`/api/videos/${v.id}/stream`" controls preload="metadata" />
            <div class="vid-info">
              <div>
                <h3>{{ v.title }}<span v-if="v.role === 1" class="private-badge">🔒</span></h3>
                <p>{{ fmtSize(v.size) }} · {{ v.created_at.slice(0, 10) }}</p>
              </div>
              <t-button size="small" variant="text" theme="danger" @click="confirmDelete(v)">删除</t-button>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <img v-img-fade :src="asset('empty')" alt="空" loading="lazy" />
          <p>架子还空着,传第一个视频</p>
        </div>
      </t-loading>
    </div>

    <!-- 上传弹窗 -->
    <t-dialog v-model:visible="upload.open" header="传视频" :confirm-btn="{ loading: upload.busy }" @confirm="doUpload">
      <div class="up-form">
        <label class="file-pick">
          <input type="file" accept="video/*" @change="pickFile" />
          <span>{{ upload.file ? `已选:${upload.file.name}(${fmtSize(upload.file.size)})` : '点这里选视频文件' }}</span>
        </label>
        <t-input v-model="upload.title" placeholder="标题(留空用文件名)" />
        <label class="private-switch"><t-switch v-model="upload.private" size="small" /> 收进小屋(role=1)</label>
      </div>
    </t-dialog>
  </div>
</template>

<style scoped>
.hero-sub { margin: 6px 0 0; color: #fff; opacity: 0.92; font-size: 14px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
.hint { margin: 0; color: var(--ink-soft); font-size: 14px; }
.vid-grid { display: grid; gap: 18px; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }
.vid-card video { width: 100%; aspect-ratio: 16/9; background: #06202f; display: block; }
.vid-info { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px 14px; gap: 8px; }
.vid-info h3 { margin: 0 0 4px; font-size: 15px; color: var(--ink); }
.vid-info p { margin: 0; font-size: 12px; color: var(--ink-soft); }
.private-badge { margin-left: 6px; }
.up-form { display: flex; flex-direction: column; gap: 14px; }
.file-pick span {
  display: block; padding: 14px; text-align: center; cursor: pointer;
  border: 1.5px dashed var(--sea-mid); border-radius: 10px;
  color: var(--ink-soft); font-size: 13px;
}
.file-pick input { display: none; }
.private-switch { display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--ink-soft); }
.load-error { color: #c33; padding: 20px 0; }
</style>
