<script setup lang="ts">
// 照片墙:对接后端 /api/photo 六件套(9/16 已实现,这次前端换正主)。
// 出图走 <img src=/api/photo/{id}/file>:HttpOnly cookie 自动随请求带上,
// 隐私图未解锁时后端回 404,前端不用也不该做二次把关。
// 分页参数是 page_size(diary 用 size,photo 用 page_size —— 各端点自己的口径,以代码为准)。
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { DialogPlugin, MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http, postForm } from '@/api/http'
import type { PageResult, Photo } from '@/api/types'
import { asset } from '@/stores/season'
import StageHero from '@/components/StageHero.vue'

const PAGE_SIZE = 24 // 一墙 24 张,更多按钮翻页

const photos = ref<Photo[]>([])
const total = ref(0)
const loading = ref(true)
const error = ref('')

const upload = reactive({ open: false, file: null as File | null, type: '', private: false, busy: false })
const viewer = ref<Photo | null>(null) // 大图预览(lightbox)

function srcOf(p: Photo) {
  return `/api/photo/${p.id}/file`
}

function fmtSize(n: number) {
  if (n > 1 << 20) return (n / (1 << 20)).toFixed(1) + ' MB'
  return Math.round(n / 1024) + ' KB'
}

async function load(append = false) {
  loading.value = true
  error.value = ''
  try {
    const page = append ? Math.floor(photos.value.length / PAGE_SIZE) + 1 : 1
    const res = await http.get<PageResult<Photo>>(`/api/photo/page?page=${page}&page_size=${PAGE_SIZE}`)
    photos.value = append ? photos.value.concat(res.data) : res.data
    total.value = res.count
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function doUpload() {
  if (!upload.file) {
    MessagePlugin.warning('先选一张图片')
    return
  }
  upload.busy = true
  const form = new FormData()
  form.append('file', upload.file)
  form.append('type', upload.type.trim())
  form.append('role', upload.private ? '1' : '0')
  try {
    const created = await postForm<Photo>('/api/photo', form)
    MessagePlugin.success(upload.private ? '已收进小屋' : `钉上墙了:${created.name}`)
    Object.assign(upload, { open: false, file: null, type: '', private: false })
    await load()
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '上传失败')
  } finally {
    upload.busy = false
  }
}

function confirmDelete(p: Photo) {
  const dlg = DialogPlugin.confirm({
    header: '删掉这张照片?',
    body: `「${p.name}」(${fmtSize(p.size)}) 盘上的原图会一起删掉。`,
    theme: 'warning',
    onConfirm: async () => {
      await http.del(`/api/photo/${p.id}`)
      dlg.hide()
      await load()
    },
  })
}

function pickFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  upload.file = f
}

// Esc 关预览
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') viewer.value = null
}
onMounted(() => {
  load()
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div>
    <StageHero
      :img="asset('banner-photos')" title="照片"
      en="photos · pinned to the wall" line="挑出来的钉成一面墙,原图在后端落盘"
    />

    <div class="page-floor">
      <div class="site-main">
        <div class="toolbar">
          <p class="hint">{{ total ? `${total} 张在墙上` : '' }}</p>
          <t-button theme="primary" @click="upload.open = true">传照片</t-button>
        </div>

        <t-loading :loading="loading && !photos.length" class="load-region">
          <p v-if="error" class="load-error">{{ error }}</p>
          <template v-else-if="photos.length">
            <div class="ph-grid stagger">
              <figure v-for="(p, i) in photos" :key="p.id" class="glass-card ph-card" :style="{ '--i': i % PAGE_SIZE }">
                <button class="ph-shot" type="button" :aria-label="`放大看 ${p.name}`" @click="viewer = p">
                  <img v-img-fade :src="srcOf(p)" :alt="p.name" loading="lazy" />
                </button>
                <figcaption>
                  <div class="ph-meta">
                    <strong>{{ p.name }}</strong>
                    <em>{{ p.type ? `${p.type} · ` : '' }}{{ p.created_at.slice(0, 10) }} · {{ fmtSize(p.size) }}</em>
                  </div>
                  <t-button size="small" variant="text" theme="danger" @click="confirmDelete(p)">删除</t-button>
                </figcaption>
              </figure>
            </div>
            <p v-if="photos.length < total" class="more-row">
              <t-button variant="outline" :loading="loading" @click="load(true)">还有 {{ total - photos.length }} 张,继续挂</t-button>
            </p>
          </template>
          <div v-else-if="!loading" class="empty-state">
            <img v-img-fade :src="asset('empty')" alt="空" loading="lazy" />
            <p>墙还空着,钉第一张照片</p>
          </div>
        </t-loading>
      </div>
    </div>

    <!-- 上传弹窗 -->
    <t-dialog v-model:visible="upload.open" header="传照片" :confirm-btn="{ loading: upload.busy }" @confirm="doUpload">
      <div class="up-form">
        <label class="file-pick">
          <input type="file" accept="image/*" @change="pickFile" />
          <span>{{ upload.file ? `已选:${upload.file.name}(${fmtSize(upload.file.size)})` : '点这里选图片(jpg/png/gif/webp/bmp)' }}</span>
        </label>
        <t-input v-model="upload.type" maxlength="20" placeholder="分类标签,如 2026夏(可留空,≤20 字)" />
        <label class="private-switch"><t-switch v-model="upload.private" size="small" /> 收进小屋(不在墙上露出)</label>
      </div>
    </t-dialog>

    <!-- 大图预览:点背景/Esc 关 -->
    <div v-if="viewer" class="lightbox" @click="viewer = null">
      <figure @click.stop>
        <img :src="srcOf(viewer)" :alt="viewer.name" />
        <figcaption>{{ viewer.name }} · {{ viewer.created_at.slice(0, 16) }}</figcaption>
      </figure>
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
.hint { margin: 0; color: var(--ink-soft); font-size: 14px; }
/* 加载期占位高度,数据到位前不塌缩跳动 */
.load-region { min-height: 260px; }
.ph-grid { display: grid; gap: 18px; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); }
.ph-card { display: flex; flex-direction: column; }
.ph-shot {
  border: none; background: none; padding: 0; cursor: zoom-in; display: block;
  font: inherit; color: inherit;
}
.ph-shot img { width: 100%; aspect-ratio: 4/3; object-fit: cover; display: block; transition: transform 0.4s ease; }
.ph-card:hover .ph-shot img { transform: scale(1.04); }
.ph-card figcaption {
  display: flex; justify-content: space-between; align-items: center; gap: 8px;
  padding: 10px 14px 12px;
}
.ph-meta { min-width: 0; }
.ph-meta strong {
  display: block; font-size: 14px; font-weight: 500; color: var(--ink);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.ph-meta em { display: block; font-style: normal; font-size: 12px; color: var(--ink-soft); margin-top: 2px; }
.more-row { text-align: center; margin: 26px 0 4px; }
.up-form { display: flex; flex-direction: column; gap: 14px; }
.file-pick span {
  display: block; padding: 14px; text-align: center; cursor: pointer;
  border: 1.5px dashed var(--sea-mid); border-radius: 10px;
  color: var(--ink-soft); font-size: 13px;
}
.file-pick input { display: none; }
.private-switch { display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--ink-soft); }
.load-error { color: #c33; padding: 20px 0; }

/* 大图预览:夜色压场,图撑到 88vw/82vh 内等比 */
.lightbox {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(6, 24, 38, 0.86);
  backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  cursor: zoom-out;
  animation: fade-in 0.25s ease backwards;
}
.lightbox figure { margin: 0; text-align: center; }
.lightbox img { max-width: 88vw; max-height: 82vh; border-radius: 10px; box-shadow: 0 30px 80px -20px rgba(0, 0, 0, 0.7); }
.lightbox figcaption { margin-top: 12px; font-size: 13px; color: rgba(230, 244, 252, 0.85); }
@keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
</style>
