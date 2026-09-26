<script setup lang="ts">
// 日记列表:对接 /api/diary/page(后端三层模板)。
// role=1 的隐私日记由服务端在未解锁时直接过滤,前端不做判断也不该做。
// 9/17 重塑批2:PageHero→StageHero 全屏舞台,内容抬进 .page-floor 地板带。
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '@/api/http'
import type { Diary, PageResult } from '@/api/types'
import { asset } from '@/stores/season'
import StageHero from '@/components/StageHero.vue'

const router = useRouter()
const diaries = ref<Diary[]>([])
const total = ref(0)
const page = ref(1)
const size = 10
const keyword = ref('')
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get<PageResult<Diary>>(
      // 9/26 验收修:size→page_size(参数名对不上后端一直在吃默认值,没撞坏纯属 size 恰好=10);
      // keyword 后端原本没这个参数=假动作,同日已在 diary 三层补上 LIKE 模糊搜
      `/api/diary/page?page=${page.value}&page_size=${size}&keyword=${encodeURIComponent(keyword.value)}`,
    )
    diaries.value = res.data
    total.value = res.count
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <StageHero
      :img="asset('banner-notes')" title="日记"
      en="notes · a private coast" line="markdown 原样落库,隐私篇目收在小屋里"
    />

    <div class="page-floor">
      <div class="site-main">
        <div class="toolbar">
          <t-input
            v-model="keyword" placeholder="搜标题/正文,回车即搜" clearable
            style="max-width: 280px" @enter="() => { page = 1; load() }" @clear="() => { page = 1; load() }"
          />
          <t-button theme="primary" @click="router.push('/notes/new')">写一篇新的</t-button>
        </div>

        <t-loading :loading="loading" class="load-region">
          <p v-if="error" class="load-error">{{ error }}(后端起了吗?uv run python runApp.py)</p>
          <div v-else-if="diaries.length" class="note-grid stagger">
            <router-link
              v-for="(d, i) in diaries" :key="d.id" :to="`/notes/${d.id}`"
              class="glass-card note-card" :style="{ '--i': i }"
            >
              <h3>{{ d.title }}</h3>
              <p class="excerpt">{{ d.content.slice(0, 66) }}{{ d.content.length > 66 ? '…' : '' }}</p>
              <div class="note-meta">
                <span>{{ d.created_at.slice(0, 16) }}</span>
                <span v-if="d.role === 1" class="private-badge">小屋</span>
              </div>
            </router-link>
          </div>
          <div v-else-if="!loading" class="empty-state">
            <img v-img-fade :src="asset('empty')" alt="空" loading="lazy" />
            <p>{{ keyword ? '这个关键词没搜到,换个词试试' : '海还空着,写下第一篇' }}</p>
          </div>
        </t-loading>

        <t-pagination
          v-if="total > size" v-model="page" :total="total" :page-size="size"
          :show-jumper="false" class="pager" @change="load"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
.toolbar :deep(.t-button) { margin-left: auto; }
/* 加载期占位高度,数据到位前不塌缩跳动 */
.load-region { min-height: 260px; }
.note-grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }
.note-card { padding: 18px 20px; display: block; transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease; }
.note-card:hover {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--sea-mid) 55%, var(--line));
  box-shadow: 0 16px 34px -16px rgba(20, 90, 140, 0.38);
}
.note-card h3 { margin: 0 0 8px; font-size: 17px; color: var(--ink); }
.excerpt {
  margin: 0 0 12px; font-size: 13px; color: var(--ink-soft); line-height: 1.65;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.note-meta { display: flex; gap: 10px; flex-wrap: wrap; font-size: 12.5px; color: var(--ink-soft); }
.private-badge {
  font-size: 11px; color: var(--private-warm);
  background: color-mix(in srgb, var(--sand) 70%, transparent);
  padding: 2px 8px; border-radius: 999px;
}
.pager { margin-top: 24px; }
.load-error { color: #c33; padding: 20px 0; }
</style>
