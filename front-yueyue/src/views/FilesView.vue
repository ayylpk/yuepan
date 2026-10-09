<script setup lang="ts">
// 资料架(9/17 新页):对接后端 /api/file 七件套(上传/分页/详情/直览/下载/改名/删除)。
// 口径:原名上盘(所见即盘上所存),改名=磁盘同步 move,删除连盘一起销。
// 直览四分发:图片/PDF/文本代码(套 CodePane 高亮)站内看;office/压缩包"请下载查看"。
// 上传的 role=1 条目进小屋货架(PrivateView),这页只列公开(role=0,服务端筛)。
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { DialogPlugin, MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http, postForm } from '@/api/http'
import type { FileEntry, PageResult } from '@/api/types'
import { asset } from '@/stores/season'
import { useAuthStore } from '@/stores/auth'
import { langOf } from '@/utils/code'
import CodePane from '@/components/CodePane.vue'
import StageHero from '@/components/StageHero.vue'

const PAGE_SIZE = 20 // 一页 20 条(10/09 统一口径:三页都用分页控件,不再"继续上架")

const auth = useAuthStore()
const files = ref<FileEntry[]>([])
const total = ref(0)
const page = ref(1)
const loading = ref(true)
const error = ref('')

const upload = reactive({ open: false, file: null as File | null, private: false, busy: false })
const rename = reactive({ open: false, target: null as FileEntry | null, value: '', busy: false })

// 直览弹窗:preview 非空即打开;text 类先 fetch /raw 再喂 CodePane
const preview = ref<FileEntry | null>(null)
const previewText = ref('')
const previewBusy = ref(false)

type Kind = 'image' | 'pdf' | 'text' | 'other'
const IMG_EXT = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'])
const TEXT_EXT = new Set(['txt', 'md', 'markdown', 'log', 'csv', 'json', 'yml', 'yaml', 'toml', 'ini', 'conf', 'sql', 'sh', 'py', 'java', 'js', 'ts', 'css', 'vue', 'go', 'rs', 'c', 'h', 'xml'])
function kindOf(f: FileEntry): Kind {
  const t = (f.type || '').toLowerCase()
  if (t === 'pdf') return 'pdf'
  if (IMG_EXT.has(t)) return 'image'
  if (TEXT_EXT.has(t)) return 'text'
  return 'other' // office/zip 等:浏览器渲染不了,只给下载(用户拍板口径)
}

const rawUrl = (f: FileEntry) => `/api/file/${f.id}/raw`
const dlUrl = (f: FileEntry) => `/api/file/${f.id}/download`
const fmtSize = (n: number) => (n > 1 << 20 ? (n / (1 << 20)).toFixed(1) + ' MB' : Math.round(n / 1024) + ' KB')

async function load() {
  loading.value = true
  error.value = ''
  try {
    // 分页参数名是 page_size(file 端点自己的口径;diary 那边叫 size,以各端代码为准)
    const res = await http.get<PageResult<FileEntry>>(`/api/file/page?page=${page.value}&page_size=${PAGE_SIZE}`)
    files.value = res.data
    total.value = res.count
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function openPreview(f: FileEntry) {
  preview.value = f
  previewText.value = ''
  if (kindOf(f) !== 'text') return // 图/pdf 由 img/iframe 自己拉 raw
  previewBusy.value = true
  try {
    const res = await fetch(rawUrl(f)) // 非 JSON 流,不吃 http 薄封装(它按 Result 拆包)
    if (!res.ok) {
      const j = (await res.json().catch(() => null)) as { detail?: string } | null
      throw new Error(j?.detail || `读取失败(${res.status})`)
    }
    previewText.value = await res.text()
  } catch (e) {
    MessagePlugin.error(e instanceof Error ? e.message : '读取失败')
    preview.value = null
  } finally {
    previewBusy.value = false
  }
}

async function doUpload() {
  if (!upload.file) {
    MessagePlugin.warning('先选一个文件')
    return
  }
  upload.busy = true
  const form = new FormData()
  form.append('file', upload.file)
  form.append('role', upload.private ? '1' : '0') // 上传入参:file + role,扩展名后端自己取
  try {
    const created = await postForm<FileEntry>('/api/file', form)
    MessagePlugin.success(upload.private ? `已收进小屋:${created.name}` : `已上架:${created.name}`)
    Object.assign(upload, { open: false, file: null, private: false })
    await load()
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '上传失败')
  } finally {
    upload.busy = false
  }
}

function pickFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) upload.file = f
}

function startRename(f: FileEntry) {
  Object.assign(rename, { open: true, target: f, value: f.name })
}
async function doRename() {
  if (!rename.target) return
  const next = rename.value.trim()
  if (!next || next === rename.target.name) {
    rename.open = false
    return
  }
  rename.busy = true
  try {
    await http.put<FileEntry>(`/api/file/${rename.target.id}`, { name: next })
    MessagePlugin.success('已改名(磁盘上的文件一起变了)')
    rename.open = false
    await load()
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '改名失败')
  } finally {
    rename.busy = false
  }
}

function confirmDelete(f: FileEntry) {
  const dlg = DialogPlugin.confirm({
    header: '删掉这份资料?',
    body: `「${f.name}」(${fmtSize(f.size)}) 会连磁盘文件一起销毁 —— 盘上就是这个名字,删了就是真没了。`,
    theme: 'warning',
    onConfirm: async () => {
      try {
        await http.del(`/api/file/${f.id}`)
        await load()
      } catch (e) {
        MessagePlugin.error(e instanceof ApiError ? e.message : '删除失败')
      } finally {
        dlg.hide()
      }
    },
  })
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') preview.value = null
}
onMounted(() => {
  load()
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div>
    <!-- 和照片墙共用一张舞台图:两个页面本来就是同一间仓库的东墙和西墙 -->
    <StageHero
      variant="banner" :img="asset('banner-photos')" title="资料"
      en="files · the shelf" line="原名落盘;图片、PDF、文本代码点开即看,其余请下载"
    />

    <div class="site-main">
        <div class="toolbar">
          <p class="hint">{{ total ? `${total} 份在架` : '' }}</p>
          <t-button theme="primary" @click="upload.open = true">传资料</t-button>
        </div>

        <t-loading :loading="loading && !files.length" class="load-region">
          <p v-if="error" class="load-error">{{ error }}</p>
          <template v-else-if="files.length">
            <ul class="fl-list stagger">
              <li v-for="(f, i) in files" :key="f.id" class="card fl-row" :style="{ '--i': i % PAGE_SIZE }">
                <button type="button" class="fl-open" :aria-label="`打开 ${f.name}`" @click="openPreview(f)">
                  <span class="fl-ext" :class="`k-${kindOf(f)}`">{{ f.type || 'file' }}</span>
                  <span class="fl-text">
                    <strong>{{ f.name }}</strong>
                    <em>{{ f.created_at.slice(0, 10) }} · {{ fmtSize(f.size) }}</em>
                  </span>
                </button>
                <span class="fl-ops">
                  <a class="fl-op" :href="dlUrl(f)">下载</a>
                  <t-button v-if="auth.loggedIn" size="small" variant="text" @click="startRename(f)">改名</t-button>
                  <t-button v-if="auth.loggedIn" size="small" variant="text" theme="danger" @click="confirmDelete(f)">删除</t-button>
                </span>
              </li>
            </ul>
            <t-pagination
              v-if="total > PAGE_SIZE" v-model="page" :total="total" :page-size="PAGE_SIZE"
              :show-jumper="false" class="pager" @change="load"
            />
          </template>
          <div v-else-if="!loading" class="empty-state">
            <img v-img-fade :src="asset('empty')" alt="空" loading="lazy" />
            <p>架子还空,传第一份资料上来</p>
          </div>
        </t-loading>
    </div>

    <!-- 上传弹窗 -->
    <t-dialog v-model:visible="upload.open" header="传资料" :confirm-btn="{ loading: upload.busy }" @confirm="doUpload">
      <div class="up-form">
        <label class="file-pick">
          <input type="file" @change="pickFile" />
          <span>{{ upload.file ? `已选:${upload.file.name}(${fmtSize(upload.file.size)})` : '点这里选文件(≤50MB,可执行类不收)' }}</span>
        </label>
        <label class="private-switch"><t-switch v-model="upload.private" size="small" /> 收进小屋(不在架上露出)</label>
      </div>
    </t-dialog>

    <!-- 改名弹窗:这是真改名,不是改标签 -->
    <t-dialog v-model:visible="rename.open" header="改文件名" :confirm-btn="{ loading: rename.busy }" @confirm="doRename">
      <div class="up-form">
        <t-input v-model="rename.value" maxlength="120" placeholder="新文件名(连扩展名一起写)" />
        <p class="rn-tip">磁盘上的文件会跟着改名;扩展名换了,类型徽章和预览方式也跟着换。同架上不能重名。</p>
      </div>
    </t-dialog>

    <!-- 直览弹窗:四类分发;点 Esc/叉关 -->
    <t-dialog
      :visible="!!preview" :header="preview?.name" width="min(1040px, 94vw)"
      :footer="false" @close="preview = null"
    >
      <template v-if="preview">
        <img v-if="kindOf(preview) === 'image'" class="pv-img" :src="rawUrl(preview)" :alt="preview.name" />
        <iframe v-else-if="kindOf(preview) === 'pdf'" class="pv-pdf" :src="rawUrl(preview)" :title="preview.name" />
        <t-loading v-else-if="kindOf(preview) === 'text'" :loading="previewBusy">
          <div class="pv-text"><CodePane :content="previewText" :lang="langOf(preview.name)" /></div>
        </t-loading>
        <div v-else class="pv-off">
          <p>.{{ preview.type || '?' }} 这个格式浏览器看不了,下载后用本地软件打开。</p>
          <t-button theme="primary" tag="a" :href="dlUrl(preview)">下载文件</t-button>
        </div>
        <p v-if="kindOf(preview) !== 'other'" class="pv-ops">
          <a class="fl-op" :href="dlUrl(preview)">下载原件</a>
        </p>
      </template>
    </t-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
.hint { margin: 0; color: var(--ink-soft); font-size: 14px; }
/* 加载期占位高度,数据到位前不塌缩跳动 */
.load-region { min-height: 260px; }
.fl-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 12px; }
.fl-row { display: flex; align-items: center; gap: 10px; padding: 10px 14px; }
.fl-open {
  display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0;
  border: none; background: none; padding: 0; font: inherit; color: inherit;
  text-align: left; cursor: pointer;
}
/* 类型徽章:配色按四档预览身份走,一眼看出点不点得开。
   四色是"按能不能站内打开"分的语义档,不是装饰色,所以不随季(令牌见 style.css :root) */
.fl-ext {
  flex: none; min-width: 46px; text-align: center; text-transform: uppercase;
  font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.04em;
  padding: 5px 7px; border-radius: 7px; color: #fff;
}
.k-image { background: var(--badge-image); }
.k-pdf { background: var(--badge-pdf); }
.k-text { background: var(--sea-mid); }
.k-other { background: var(--badge-other); }
.fl-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.fl-text strong {
  font-size: 14px; font-weight: 500; color: var(--ink);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.fl-text em { font-style: normal; font-size: 12px; color: var(--ink-soft); }
.fl-ops { display: flex; align-items: center; gap: 4px; flex: none; }
.fl-op { font-size: 13px; color: var(--brand); text-decoration: none; padding: 4px 8px; border-radius: 8px; }
.fl-op:hover { background: var(--cloud); }
.pager { margin-top: 24px; }
.load-error { color: #c33; padding: 20px 0; }

.up-form { display: flex; flex-direction: column; gap: 14px; }
.file-pick span {
  display: block; padding: 14px; text-align: center; cursor: pointer;
  border: 1.5px dashed var(--sea-mid); border-radius: 10px;
  color: var(--ink-soft); font-size: 13px;
}
.file-pick input { display: none; }
.private-switch { display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--ink-soft); }
.rn-tip { margin: 0; font-size: 12px; color: var(--ink-soft); }

/* 直览弹窗各体 */
.pv-img { display: block; max-width: 100%; max-height: 68vh; margin: 0 auto; border-radius: 8px; }
.pv-pdf { display: block; width: 100%; height: 68vh; border: none; border-radius: 8px; background: var(--code-bg); }
.pv-text { max-height: 68vh; overflow: auto; background: var(--code-bg); border-radius: 10px; }
.pv-off { text-align: center; padding: 30px 0 26px; color: var(--ink-soft); }
.pv-off p { margin: 0 0 16px; }
.pv-ops { margin: 12px 0 0; text-align: right; }
</style>
