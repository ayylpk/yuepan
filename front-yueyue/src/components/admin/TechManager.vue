<script setup lang="ts">
// 技术栈字典管理(设置页 · 仅登录可见)。
// 规则都在后端(/api/tech):大小写归一、撞名幂等、被引用 409 —— 这里只展示 + 转发。
import { onMounted, reactive, ref } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http } from '@/api/http'
import type { PageResult, Tech } from '@/api/types'

const rows = ref<Tech[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const loading = ref(false)

// 新增:一行内联输入就够,不值得开弹窗
const adding = reactive({ visible: false, name: '', busy: false })
// 改名:记住改的是哪条
const renaming = reactive({ visible: false, id: 0, name: '', busy: false })

const cols = [
  { colKey: 'name', title: '名称', width: 160 },
  { colKey: 'ref_count', title: '被引用', width: 90 },
  { colKey: 'created_at', title: '创建于', width: 170 },
  { colKey: 'op', title: '操作', width: 140 },
]

function fail(e: unknown, fallback: string) {
  MessagePlugin.error(e instanceof ApiError ? e.message : fallback)
}

async function load() {
  loading.value = true
  try {
    const q = new URLSearchParams({ page: String(page.value), page_size: String(pageSize.value) })
    if (keyword.value.trim()) q.set('keyword', keyword.value.trim())
    const res = await http.get<PageResult<Tech>>(`/api/tech/page?${q}`)
    rows.value = res.data
    total.value = res.count
  } catch (e) {
    fail(e, '技术栈列表加载失败')
  } finally {
    loading.value = false
  }
}

async function doAdd() {
  if (!adding.name.trim()) return MessagePlugin.warning('名称不能为空')
  adding.busy = true
  try {
    const tech = await http.post<Tech>('/api/tech', { name: adding.name.trim() })
    MessagePlugin.success(`已保存「${tech.name}」(大小写撞车时返回的是已有那条)`)
    adding.visible = false
    adding.name = ''
    await load()
  } catch (e) {
    fail(e, '新增失败')
  } finally {
    adding.busy = false
  }
}

function startRename(row: Tech) {
  Object.assign(renaming, { visible: true, id: row.id, name: row.name })
}

async function doRename() {
  if (!renaming.name.trim()) return MessagePlugin.warning('名称不能为空')
  renaming.busy = true
  try {
    await http.put<Tech>(`/api/tech/${renaming.id}`, { name: renaming.name.trim() })
    MessagePlugin.success('已改名')
    renaming.visible = false
    await load()
  } catch (e) {
    fail(e, '改名失败') // 撞名 409 的 detail 后端写好了人话,直接透传
  } finally {
    renaming.busy = false
  }
}

async function doDelete(row: Tech) {
  try {
    await http.del(`/api/tech/${row.id}`)
    MessagePlugin.success(`已删除「${row.name}」`)
    await load()
  } catch (e) {
    fail(e, '删除失败') // 被引用 409:「还有 N 个项目在用,先去项目里解绑」
  }
}

onMounted(load)
</script>

<template>
  <section class="card admin-card">
    <header class="admin-head">
      <h2>技术栈字典</h2>
      <div class="admin-tools">
        <t-input v-model="keyword" placeholder="搜名称(不分大小写)" clearable style="width: 180px" @enter="page = 1; load()" />
        <t-button size="small" variant="outline" @click="page = 1; load()">搜索</t-button>
        <t-button size="small" theme="primary" @click="adding.visible = true">＋ 新增</t-button>
      </div>
    </header>

    <t-table
      :data="rows" :columns="cols" row-key="id" :loading="loading" size="small"
      empty="还没有技术栈,点右上角新增一条"
    >
      <template #name="{ row }"><span class="mono">{{ row.name }}</span></template>
      <template #ref_count="{ row }">
        <t-tag :theme="row.ref_count ? 'primary' : 'default'" variant="light" size="small">{{ row.ref_count }} 项目</t-tag>
      </template>
      <template #created_at="{ row }"><span class="dim">{{ row.created_at.slice(0, 16) }}</span></template>
      <template #op="{ row }">
        <t-button size="small" variant="text" theme="primary" @click="startRename(row)">改名</t-button>
        <t-popconfirm content="删除后不可恢复,确认?" @confirm="doDelete(row)">
          <t-button size="small" variant="text" theme="danger">删除</t-button>
        </t-popconfirm>
      </template>
    </t-table>

    <t-pagination
      v-model="page" v-model:page-size="pageSize" :total="total" :show-jumper="false"
      size="small" @change="load"
    />

    <t-dialog v-model:visible="adding.visible" header="新增技术栈" :confirm-btn="{ loading: adding.busy }" @confirm="doAdd">
      <t-input v-model="adding.name" placeholder="名字,如 Vue / FastAPI(存的时候自动归一大小写)" @enter="doAdd" />
      <p class="tip">和已有条目只是大小写不同时不会重复建,直接复用那条。</p>
    </t-dialog>

    <t-dialog v-model:visible="renaming.visible" header="改名字" :confirm-btn="{ loading: renaming.busy }" @confirm="doRename">
      <t-input v-model="renaming.name" placeholder="新名字" @enter="doRename" />
      <p class="tip">撞到别的条目会拒绝(要合并:改绑项目 → 删旧条目)。</p>
    </t-dialog>
  </section>
</template>

<style scoped>
.admin-card { padding: 20px 22px; display: flex; flex-direction: column; gap: 14px; }
.admin-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.admin-head h2 { margin: 0; font-size: 17px; color: var(--ink); }
.admin-tools { display: flex; gap: 8px; align-items: center; }
.mono { font-family: var(--font-mono); font-size: 13px; color: var(--ink); }
.dim { font-size: 12px; color: var(--ink-soft); }
.tip { margin: 10px 0 0; font-size: 12px; color: var(--ink-soft); }
</style>
