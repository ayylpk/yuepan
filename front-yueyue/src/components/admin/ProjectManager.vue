<script setup lang="ts">
// 项目管理(设置页 · 仅登录可见):项目 CRUD + 技术栈弹窗匹配 + 本机目录挂载。
// 两个不显眼但重要的约定:
//   1. 编辑回显走 GET /api/projects/{id}/manage —— 公开列表里根本没有 path 字段(防泄露本机目录);
//   2. path 变更后顺手 POST /api/code/reindex —— 不重建的话代码页看到的还是旧目录的树。
import { onMounted, reactive, ref } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http } from '@/api/http'
import type { Project, ProjectManage, Tech } from '@/api/types'

const rows = ref<Project[]>([])
const loading = ref(false)
const techDict = ref<Tech[]>([]) // 弹窗选项源(量小,一次全拿)

const cols = [
  { colKey: 'name', title: '项目', width: 180 },
  { colKey: 'period', title: '时间段', width: 130 },
  { colKey: 'tech', title: '技术栈' },
  { colKey: 'repo', title: '代码', width: 90 },
  { colKey: 'op', title: '操作', width: 210 },
]

// —— 新增 / 编辑表单(两种模式共用一个 dialog,edit 时带 id) ——
const emptyForm = { id: 0, name: '', code: '📦', period: '', description: '', path: '', repo: '', tech_names: [] as string[] }
const form = reactive({ ...emptyForm })
const formVisible = ref(false)
const formBusy = ref(false)
const isEdit = () => form.id > 0

// —— 技术栈弹窗(独立于基本信息编辑:后端 PUT 项目本来就不带 tech,两个意图各管各) ——
const bind = reactive({ visible: false, id: 0, name: '', names: [] as string[], busy: false })

function fail(e: unknown, fallback: string) {
  MessagePlugin.error(e instanceof ApiError ? e.message : fallback)
}

async function load() {
  loading.value = true
  try {
    rows.value = await http.get<Project[]>('/api/projects')
  } catch (e) {
    fail(e, '项目列表加载失败')
  } finally {
    loading.value = false
  }
}

async function loadTechDict() {
  try {
    techDict.value = await http.get<Tech[]>('/api/tech/list')
  } catch (e) {
    fail(e, '技术栈字典加载失败')
  }
}

function startCreate() {
  Object.assign(form, emptyForm, { tech_names: [] })
  formVisible.value = true
}

async function startEdit(row: Project) {
  // 先拿到 manage 回显再开弹窗:拿不到就压根不给编辑 ——
  // 若开着弹窗而 path 是空的,用户点保存 = 静默"摘除本机目录",这是数据事故不是体验问题。
  let m: ProjectManage
  try {
    m = await http.get<ProjectManage>(`/api/projects/${row.id}/manage`)
  } catch (e) {
    return fail(e, '回显项目详情失败,稍后再试')
  }
  // repo 列在后端被折叠过(空则回退 name),等于 name 时还原成空,让输入框显示占位文案
  Object.assign(form, emptyForm, {
    id: row.id, name: row.name, code: row.code, period: row.period,
    description: row.desc, path: m.path, repo: m.repo === row.name || m.repo === null ? '' : m.repo,
  })
  formVisible.value = true
}

async function save() {
  if (!form.name.trim()) return MessagePlugin.warning('项目名不能为空')
  formBusy.value = true
  try {
    if (isEdit()) {
      await http.put<Project>(`/api/projects/${form.id}`, {
        name: form.name.trim(), code: form.code || '📦', period: form.period,
        description: form.description, path: form.path, repo: form.repo,
      })
      // path 动了就重建索引,否则代码页是旧目录的树
      if (form.path.trim()) await reindexQuiet(form.repo || form.name)
    } else {
      await http.post<Project>('/api/projects', {
        name: form.name.trim(), code: form.code || '📦', period: form.period,
        description: form.description, path: form.path, repo: form.repo,
        tech_names: form.tech_names,
      })
      if (form.path.trim()) await reindexQuiet(form.repo || form.name)
    }
    MessagePlugin.success(isEdit() ? '已保存' : '项目已创建')
    formVisible.value = false
    await load()
  } catch (e) {
    fail(e, '保存失败')
  } finally {
    formBusy.value = false
  }
}

/** reindex 失败不拦保存(目录可能是暂时拔掉的 U 盘),降级成 warning */
async function reindexQuiet(repo: string) {
  try {
    await http.post(`/api/code/reindex?repo=${encodeURIComponent(repo)}`)
  } catch {
    MessagePlugin.warning('索引重建失败:去代码页手动点「重建索引」,或检查目录路径是否写对')
  }
}

function startBind(row: Project) {
  Object.assign(bind, { visible: true, id: row.id, name: row.name, names: [...row.tech] })
  if (!techDict.value.length) loadTechDict()
}

async function saveBind() {
  bind.busy = true
  try {
    const p = await http.put<Project>(`/api/projects/${bind.id}/techs`, { names: bind.names })
    MessagePlugin.success(`「${p.name}」技术栈已更新:${p.tech.join(' / ') || '(清空)'}`)
    bind.visible = false
    await load()
    await loadTechDict() // 弹窗里手输的新名字可能刚被后端自动建档
  } catch (e) {
    fail(e, '绑定失败')
  } finally {
    bind.busy = false
  }
}

async function doDelete(row: Project) {
  try {
    await http.del(`/api/projects/${row.id}`)
    MessagePlugin.success(`已删除「${row.name}」(代码索引一并解除挂载)`)
    await load()
  } catch (e) {
    fail(e, '删除失败')
  }
}

onMounted(() => {
  load()
  loadTechDict()
})
</script>

<template>
  <section class="glass-card admin-card">
    <header class="admin-head">
      <h2>项目</h2>
      <t-button size="small" theme="primary" @click="startCreate">＋ 新增项目</t-button>
    </header>

    <t-table
      :data="rows" :columns="cols" row-key="id" :loading="loading" size="small"
      empty="还没有项目,点右上角挂第一个"
    >
      <template #name="{ row }"><span class="proj">{{ row.code }} {{ row.name }}</span></template>
      <template #period="{ row }"><span class="dim">{{ row.period || '—' }}</span></template>
      <template #tech="{ row }">
        <div class="techs">
          <t-tag v-for="t in row.tech" :key="t" size="small" variant="light">{{ t }}</t-tag>
          <span v-if="!row.tech.length" class="dim">—</span>
        </div>
      </template>
      <template #repo="{ row }">
        <t-tag v-if="row.repo" theme="success" variant="light" size="small">已挂载</t-tag>
        <t-tooltip v-else content="编辑项目,填「本机目录」后才会出现在代码页" placement="top">
          <t-tag size="small" variant="outline">未挂代码</t-tag>
        </t-tooltip>
      </template>
      <template #op="{ row }">
        <t-button size="tiny" variant="text" theme="primary" @click="startEdit(row)">编辑</t-button>
        <t-button size="tiny" variant="text" theme="primary" @click="startBind(row)">技术栈</t-button>
        <t-popconfirm content="删除项目(不会动你磁盘上的文件),确认?" @confirm="doDelete(row)">
          <t-button size="tiny" variant="text" theme="danger">删除</t-button>
        </t-popconfirm>
      </template>
    </t-table>

    <!-- 新增 / 编辑 基本信息 -->
    <t-dialog
      v-model:visible="formVisible" :header="isEdit() ? '编辑项目' : '新增项目'" width="560px"
      :confirm-btn="{ loading: formBusy }" @confirm="save"
    >
      <div class="form">
        <label><span>项目名 *</span><t-input v-model="form.name" placeholder="如 月畔小站" /></label>
        <label><span>图标(emoji)</span><t-input v-model="form.code" placeholder="📦" /></label>
        <label><span>时间段</span><t-input v-model="form.period" placeholder="任意口径:2026.09 / 暑假 / 进行时…" /></label>
        <label><span>简介</span><t-textarea v-model="form.description" placeholder="一两句,展示在项目墙卡片上" :autosize="{ minRows: 2, maxRows: 4 }" /></label>
        <label>
          <span>本机目录</span>
          <t-input v-model="form.path" placeholder="相对仓库根目录,如 yueyue/front-yueyue;留空=不挂代码(公网接口不会回传这个字段)" />
        </label>
        <label><span>仓库名</span><t-input v-model="form.repo" placeholder="代码页 chip 显示名,留空用项目名" /></label>
        <label v-if="!isEdit()">
          <span>技术栈</span>
          <t-select
            v-model="form.tech_names" multiple filterable creatable clearable
            :options="techDict.map((t) => ({ label: t.name, value: t.name }))"
            placeholder="从字典挑,或直接输新名字回车(大小写撞车自动复用)"
          />
        </label>
      </div>
    </t-dialog>

    <!-- 技术栈弹窗:独立保存,和基本信息互不牵连 -->
    <t-dialog
      v-model:visible="bind.visible" :header="`技术栈 · ${bind.name}`" width="520px"
      :confirm-btn="{ loading: bind.busy }" @confirm="saveBind"
    >
      <t-select
        v-model="bind.names" multiple filterable creatable clearable
        :options="techDict.map((t) => ({ label: `${t.name}(${t.ref_count})`, value: t.name }))"
        placeholder="选已有的,或输新名字自动建档"
      />
      <p class="tip">保存 = 全量替换这份列表;括号里是它当前被几个项目引用。</p>
    </t-dialog>
  </section>
</template>

<style scoped>
.admin-card { padding: 20px 22px; display: flex; flex-direction: column; gap: 14px; }
.admin-head { display: flex; justify-content: space-between; align-items: center; }
.admin-head h2 { margin: 0; font-size: 17px; color: var(--ink); }
.proj { font-size: 13.5px; color: var(--ink); }
.dim { font-size: 12px; color: var(--ink-soft); }
.techs { display: flex; gap: 6px; flex-wrap: wrap; }
.form { display: flex; flex-direction: column; gap: 12px; }
.form label { display: grid; grid-template-columns: 88px 1fr; align-items: start; gap: 10px; }
.form label > span { font-size: 13px; color: var(--ink-soft); line-height: 34px; }
.tip { margin: 10px 0 0; font-size: 12px; color: var(--ink-soft); }
</style>
