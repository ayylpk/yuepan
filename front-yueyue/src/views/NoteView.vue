<script setup lang="ts">
// 日记详情 = 查看/编辑两态;/notes/new 直接进编辑态。
// "藏进小屋"开关 = 后端 role 字段(0 公开 / 1 隐私),PUT 支持单改 role。
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DialogPlugin, MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http } from '@/api/http'
import type { Diary } from '@/api/types'
import MarkdownView from '@/components/MarkdownView.vue'

const route = useRoute()
const router = useRouter()

const isNew = computed(() => route.name === 'note-new')
const diaryId = computed(() => (isNew.value ? null : Number(route.params.id)))

const diary = ref<Diary | null>(null)
const loading = ref(true)
const editing = ref(false)
const saving = ref(false)
const form = reactive({ title: '', content: '', private: false })

async function load() {
  loading.value = true
  if (isNew.value) {
    Object.assign(form, { title: '', content: '', private: false })
    editing.value = true
    loading.value = false
    return
  }
  try {
    diary.value = await http.get<Diary>(`/api/diary/${diaryId.value}`)
    Object.assign(form, {
      title: diary.value.title,
      content: diary.value.content,
      private: diary.value.role === 1,
    })
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '加载失败')
    router.replace('/notes')
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!form.title.trim()) {
    MessagePlugin.warning('标题总得有一个')
    return
  }
  saving.value = true
  const payload = { title: form.title.trim(), content: form.content, role: form.private ? 1 : 0 }
  try {
    if (isNew.value) {
      const created = await http.post<Diary>('/api/diary', payload)
      MessagePlugin.success('已存好')
      router.replace(`/notes/${created.id}`) // replace:回退不再经过 /notes/new
    } else {
      await http.put<Diary>(`/api/diary/${diaryId.value}`, payload)
      MessagePlugin.success('已保存')
      await load() // 回读拿新 updated_at
    }
    editing.value = false
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

function confirmDelete() {
  const dlg = DialogPlugin.confirm({
    header: '删掉这篇?',
    body: `「${form.title}」会从数据库里真的消失,没法后悔。`,
    theme: 'warning',
    onConfirm: async () => {
      await http.del(`/api/diary/${diaryId.value}`)
      MessagePlugin.success('已删除')
      dlg.hide()
      router.replace('/notes')
    },
  })
}

onMounted(load)
watch(() => route.params.id, load)
</script>

<template>
  <div class="site-main note-page">
    <t-loading :loading="loading">
      <template v-if="diary || editing">
        <div class="note-head">
          <div>
            <h2>{{ editing ? (isNew ? '新日记' : '编辑中') : form.title }}</h2>
            <p v-if="!editing" class="note-meta">
              <span>{{ diary?.created_at.slice(0, 16) }}</span>
              <span v-if="diary && diary.updated_at !== diary.created_at">改于 {{ diary.updated_at.slice(0, 16) }}</span>
              <span v-if="form.private" class="tag private">🔒 小屋</span>
            </p>
          </div>
          <div class="actions">
            <t-button v-if="!editing" theme="primary" variant="outline" @click="editing = true">编辑</t-button>
            <t-button v-if="!editing && !isNew" theme="danger" variant="text" @click="confirmDelete">删除</t-button>
            <t-button v-if="editing" theme="primary" :loading="saving" @click="save">保存</t-button>
            <t-button v-if="editing && !isNew" variant="outline" @click="load">取消</t-button>
            <t-button variant="text" @click="router.push('/notes')">← 回列表</t-button>
          </div>
        </div>

        <!-- 查看态 -->
        <MarkdownView v-if="!editing && diary" :content="diary.content" />

        <!-- 编辑态 -->
        <div v-else class="edit-form">
          <div class="edit-row">
            <t-input v-model="form.title" placeholder="标题" style="max-width: 420px" />
            <label class="private-switch">
              <t-switch v-model="form.private" size="small" /> 藏进小屋(role=1)
            </label>
          </div>
          <t-textarea
            v-model="form.content" placeholder="正文,支持 markdown(GFM 表格/代码块)"
            :autosize="{ minRows: 16, maxRows: 40 }"
          />
        </div>
      </template>
    </t-loading>
  </div>
</template>

<style scoped>
.note-page { padding-top: 36px; }
.note-head {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 16px; flex-wrap: wrap; margin-bottom: 18px;
}
.note-head h2 { margin: 0 0 6px; font-size: 26px; color: var(--ink); }
.note-meta { margin: 0; display: flex; gap: 10px; flex-wrap: wrap; font-size: 13px; color: var(--ink-soft); }
.tag { color: var(--sea-deep); }
.tag.private { color: var(--private-warm); }
.actions { display: flex; gap: 6px; flex-wrap: wrap; }
.edit-form { display: flex; flex-direction: column; gap: 14px; }
.edit-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
.private-switch { display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--ink-soft); }
</style>
