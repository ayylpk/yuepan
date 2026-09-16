<script setup lang="ts">
// 在线看代码:白名单仓库 + git ls-files 平铺路径 → 客户端拼树。
// 后端 /api/code/repos|tree|file|log 已实现;pull/reindex 两个写接口要登录,
// 按钮只对登录用户可见(路由闸门兜底,这里 v-if 只是防 OFFLINE 之外的边角)。
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import hljs from 'highlight.js'
import { MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http } from '@/api/http'
import type { RepoInfo, CommitInfo } from '@/api/types'
import { asset } from '@/stores/season'
import { useAuthStore } from '@/stores/auth'
import PageHero from '@/components/PageHero.vue'
import FileTree, { type TreeNode } from '@/components/FileTree.vue'

interface RepoTree { branch: string; count: number; files: string[] }
interface CodeFile { path: string; content: string; size: number }

const route = useRoute()
const auth = useAuthStore()
const repos = ref<RepoInfo[]>([])
const current = ref('')
const tab = ref<'files' | 'log'>('files')
const tree = ref<TreeNode | null>(null)
const commits = ref<CommitInfo[]>([])
const filePath = ref('')
const fileContent = ref<HTMLElement | null>(null)
const error = ref('')
const busy = ref(false)

const LANG_BY_EXT: Record<string, string> = {
  ts: 'typescript', js: 'javascript', vue: 'xml', json: 'json', py: 'python',
  java: 'java', css: 'css', scss: 'scss', html: 'xml', md: 'markdown',
  yml: 'yaml', yaml: 'yaml', xml: 'xml', sql: 'sql', sh: 'bash', rs: 'rust', go: 'go',
}

/** 平铺路径列表 → 嵌套树(目录在前文件在后,各自按名排序) */
function buildTree(files: string[]): TreeNode {
  const root: TreeNode = { name: '', path: '', children: [] }
  for (const full of files) {
    let node = root
    const parts = full.split('/')
    let acc = ''
    for (let i = 0; i < parts.length; i++) {
      acc = acc ? `${acc}/${parts[i]}` : parts[i]
      const isFile = i === parts.length - 1
      node.children ??= []
      let next = node.children.find((c) => c.name === parts[i] && !!c.children === !isFile)
      if (!next) {
        next = isFile ? { name: parts[i], path: acc } : { name: parts[i], path: acc, children: [] }
        node.children.push(next)
      }
      node = next
    }
  }
  const sortRec = (n: TreeNode) => {
    if (!n.children) return
    n.children.sort((a, b) => (a.children ? 0 : 1) - (b.children ? 0 : -1) || a.name.localeCompare(b.name))
    n.children.forEach(sortRec)
  }
  sortRec(root)
  return root
}

async function openRepo(name: string) {
  if (!name) return
  current.value = name
  filePath.value = ''
  error.value = ''
  busy.value = true
  try {
    const t = await http.get<RepoTree>(`/api/code/tree?repo=${encodeURIComponent(name)}`)
    tree.value = buildTree(t.files)
    commits.value = await http.get<CommitInfo[]>(`/api/code/log?repo=${encodeURIComponent(name)}&limit=50`)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
    tree.value = null
  } finally {
    busy.value = false
  }
}

async function openFile(path: string) {
  filePath.value = path
  busy.value = true
  try {
    const f = await http.get<CodeFile>(`/api/code/file?repo=${encodeURIComponent(current.value)}&path=${encodeURIComponent(path)}`)
    await paintCode(path, f.content)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '读文件失败'
  } finally {
    busy.value = false
  }
}

/** 管理动作:pull 会改文件,所以拉完顺手 reindex;两步都成功才刷树。 */
const syncBusy = ref('')
async function sync(kind: 'pull' | 'reindex') {
  if (!current.value) return
  syncBusy.value = kind
  const q = `/api/code/${kind}?repo=${encodeURIComponent(current.value)}`
  try {
    const r = await http.post<{ message: string }>(q)
    if (kind === 'pull') await http.post(`/api/code/reindex?repo=${encodeURIComponent(current.value)}`)
    MessagePlugin.success(r.message || '完成')
    await openRepo(current.value)
    repos.value = await http.get<RepoInfo[]>('/api/code/repos')
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '操作失败')
  } finally {
    syncBusy.value = ''
  }
}

async function paintCode(path: string, content: string) {
  const el = fileContent.value
  if (!el) return
  const ext = path.split('.').pop()?.toLowerCase() ?? ''
  const lang = LANG_BY_EXT[ext]
  el.textContent = ''
  const pre = document.createElement('pre')
  const code = document.createElement('code')
  if (lang) {
    code.className = `language-${lang}`
    code.textContent = content
    pre.appendChild(code)
    el.appendChild(pre)
    hljs.highlightElement(code) // 用 hljs 高亮,而不是 innerHTML 拼(避免注入面)
  } else {
    pre.textContent = content // 认不出的语言纯文本兜底
    el.appendChild(pre)
  }
}

onMounted(async () => {
  try {
    repos.value = await http.get<RepoInfo[]>('/api/code/repos')
    const fromQuery = String(route.query.repo || '')
    const hit = repos.value.find((r) => r.name === fromQuery && r.exists)
    if (hit) await openRepo(hit.name)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '仓库列表加载失败(/api/code 后端未实现)'
  }
})
watch(() => route.query.repo, async (q) => {
  const name = String(q || '')
  if (name && name !== current.value && repos.value.some((r) => r.name === name)) await openRepo(name)
})
</script>

<template>
  <div>
    <PageHero :img="asset('banner-code')" eyebrow="CODE" title="在线看代码">
      <p class="hero-sub">白名单仓库 · 树来自 git 清单,内容读的是本机工作区</p>
    </PageHero>

    <div class="site-main">
      <p v-if="error" class="load-error">{{ error }}</p>

      <div v-if="repos.length" class="repo-bar">
        <button
          v-for="r in repos" :key="r.name"
          class="glass-card repo-chip" :class="{ on: r.name === current, dead: !r.exists }"
          :disabled="!r.exists" :title="r.desc"
          @click="openRepo(r.name)"
        >
          <strong>{{ r.name }}</strong>
          <em>{{ r.exists ? `${r.branch} · ${r.last_commit}` : '本机没找到这个仓库' }}</em>
        </button>
      </div>
      <p v-else-if="!error" class="load-empty">白名单还是空的 —— 后端 /api/code/repos 没数据</p>

      <p v-if="current && auth.loggedIn" class="admin-row">
        <t-button size="tiny" variant="outline" :loading="syncBusy === 'pull'" @click="sync('pull')">⤓ git pull + 重建索引</t-button>
        <t-button size="tiny" variant="outline" :loading="syncBusy === 'reindex'" @click="sync('reindex')">⟳ 只重建索引</t-button>
        <span class="admin-hint">动磁盘的操作,登录才露这两个按钮;pull 只做快进,有分叉会原样报错</span>
      </p>

      <div v-if="current" class="workbench glass-card">
        <div class="side">
          <div class="tabs">
            <button :class="{ on: tab === 'files' }" @click="tab = 'files'">文件</button>
            <button :class="{ on: tab === 'log' }" @click="tab = 'log'">历史</button>
          </div>
          <t-loading :loading="busy">
            <div v-if="tab === 'files'" class="tree-wrap">
              <FileTree v-if="tree" :node="tree" @pick="openFile" />
            </div>
            <ol v-else class="log">
              <li v-for="c in commits" :key="c.hash">
                <code>{{ c.hash }}</code> {{ c.subject }}
                <em>{{ c.author }} · {{ c.ago }}</em>
              </li>
            </ol>
          </t-loading>
        </div>
        <div class="pane">
          <p v-if="!filePath" class="pane-hint">← 左边挑一个文件</p>
          <template v-else>
            <p class="crumb">{{ current }} / {{ filePath }}</p>
            <div ref="fileContent" class="code-body" />
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hero-sub { margin: 6px 0 0; color: #fff; opacity: 0.92; font-size: 14px; }
.repo-bar { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
.repo-chip {
  border: 1px solid var(--line); background: var(--card); cursor: pointer;
  padding: 10px 16px; border-radius: 12px; text-align: left; font-family: inherit;
  display: flex; flex-direction: column; gap: 2px;
}
.repo-chip.on { border-color: var(--brand); box-shadow: 0 0 0 2px color-mix(in srgb, var(--brand) 25%, transparent); }
.repo-chip.dead { opacity: 0.45; cursor: not-allowed; }
.repo-chip strong { font-size: 14px; color: var(--ink); }
.repo-chip em { font-style: normal; font-size: 11px; color: var(--ink-soft); font-family: var(--font-mono); }
.workbench { display: grid; grid-template-columns: 280px 1fr; min-height: 420px; }
.side { border-right: 1px solid var(--line); padding: 12px 10px 12px 12px; max-height: 70vh; overflow: auto; }
.tabs { display: flex; gap: 6px; margin-bottom: 10px; }
.tabs button {
  border: none; background: none; cursor: pointer; padding: 5px 12px; border-radius: 999px;
  font-size: 13px; color: var(--ink-soft); font-family: inherit;
}
.tabs button.on { background: var(--sea-mid); color: #fff; }
.tree-wrap { padding-right: 6px; }
.log { margin: 0; padding: 0 0 0 18px; font-size: 12.5px; color: var(--ink); }
.log li { margin: 8px 0; }
.log code { color: var(--sea-deep); margin-right: 4px; }
.log em { display: block; font-style: normal; color: var(--ink-soft); font-size: 11px; }
.pane { padding: 14px 18px; overflow: auto; max-height: 70vh; }
.pane-hint { color: var(--ink-soft); margin-top: 40px; text-align: center; }
.crumb { margin: 0 0 12px; font-family: var(--font-mono); font-size: 12.5px; color: var(--ink-soft); word-break: break-all; }
.code-body :deep(pre) { margin: 0; }
.code-body :deep(code) { background: none; padding: 0; }
.admin-row { display: flex; align-items: center; gap: 10px; margin: 0 0 14px; }
.admin-hint { font-size: 12px; color: var(--ink-soft); }
.load-error { color: #c33; margin: 0 0 16px; }
.load-empty { color: var(--ink-soft); }
@media (max-width: 860px) { .workbench { grid-template-columns: 1fr; } .side { border-right: none; border-bottom: 1px solid var(--line); } }
</style>
