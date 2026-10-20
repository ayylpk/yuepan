<script setup lang="ts">
// 动漫图片墙(10/20):/anime/:id/images
// 详情页不再直接铺图,而是「查看 / 上传」两个按钮;图片全在这里看。
// 支持 ?episode=<id> 只看某一集(详情页的「查看本集」跳这里)。
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http } from '@/api/http'
import type { AnimeImage, AnimeWork } from '@/api/types'
import ImageLightbox from '@/components/ImageLightbox.vue'

const route = useRoute()
const router = useRouter()
const workId = computed(() => Number(route.params.id))
const episodeFilter = computed(() => {
  const raw = route.query.episode
  return raw ? Number(raw) : null
})

const work = ref<AnimeWork | null>(null)
const loading = ref(true)
const index = ref<number | null>(null)

// 集 id → "第 1 季 · 第 3 集",图片墙上一眼看出哪张属于哪集
const episodeLabels = computed(() => {
  const map = new Map<number, string>()
  for (const season of work.value?.seasons ?? []) {
    for (const episode of season.episodes) {
      map.set(episode.id, `第${season.season_number}季 · 第${episode.episode_number}集`)
    }
  }
  return map
})

const images = computed<AnimeImage[]>(() => {
  const all = work.value?.images ?? []
  return episodeFilter.value ? all.filter(i => i.episode_id === episodeFilter.value) : all
})
const filterLabel = computed(() => (episodeFilter.value ? episodeLabels.value.get(episodeFilter.value) ?? '本集' : ''))

async function load() {
  loading.value = true
  try {
    work.value = await http.get<AnimeWork>(`/api/anime/${workId.value}`)
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '加载失败')
    router.replace('/anime')
  } finally {
    loading.value = false
  }
}
const open = (i: number) => { index.value = i }
const current = computed(() => (index.value === null ? null : images.value[index.value] ?? null))
const step = (delta: number) => {
  if (index.value === null) return
  const next = index.value + delta
  if (next >= 0 && next < images.value.length) index.value = next
}
const backToDetail = () => router.push(`/anime/${workId.value}`)
onMounted(load)
watch(() => route.params.id, load)
</script>
<template>
  <div class="site-main wall-page">
    <t-loading :loading="loading">
      <template v-if="work">
        <div class="wall-top">
          <header class="page-head">
            <h2>{{ work.title }} · 图片</h2>
            <p class="meta">
              <span>{{ images.length }} 张</span>
              <span v-if="episodeFilter" class="chip">{{ filterLabel }}</span>
              <span v-if="episodeFilter" class="chip-link" @click="router.replace(`/anime/${workId}/images`)">看全部</span>
            </p>
          </header>
          <div class="actions">
            <t-button variant="text" @click="backToDetail">回详情</t-button>
          </div>
        </div>

        <div v-if="!images.length" class="empty">
          {{ episodeFilter ? '这一集还没有图片。' : '还没有图片，回详情页批量上传。' }}
        </div>
        <div v-else class="wall">
          <button v-for="(image, i) in images" :key="image.id" class="tile" type="button" :aria-label="`查看：${image.name}`" @click="open(i)">
            <img :src="image.url" :alt="image.name" loading="lazy" />
            <span v-if="image.episode_id && episodeLabels.get(image.episode_id)" class="tile-tag">{{ episodeLabels.get(image.episode_id) }}</span>
          </button>
        </div>

        <ImageLightbox
          v-if="current && index !== null"
          :src="current.url" :alt="current.name"
          :caption="`${index + 1} / ${images.length} · ${current.name}`"
          :has-prev="index > 0" :has-next="index < images.length - 1"
          @prev="step(-1)" @next="step(1)" @close="index = null"
        />
      </template>
    </t-loading>
  </div>
</template>
<style scoped>
.wall-page { padding-top: 32px; }
.wall-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; margin-bottom: 22px; }
.wall-top .page-head { margin-bottom: 0; }
.meta { margin: 8px 0 0; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 13px; color: var(--ink-soft); }
.chip { padding: 2px 8px; border-radius: 999px; background: color-mix(in srgb, var(--cloud) 60%, var(--card)); color: var(--ink-soft); font-size: 12px; }
.chip-link { color: var(--brand); font-size: 12px; cursor: pointer; }
.actions { display: flex; gap: 6px; flex-wrap: wrap; }
.empty { padding: 48px 0; color: var(--ink-soft); }
.wall { display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(168px, 1fr)); }
.tile {
  position: relative; padding: 0; overflow: hidden; cursor: zoom-in;
  aspect-ratio: 4 / 3; border: 1px solid var(--line); border-radius: 10px; background: var(--cloud);
}
.tile img { display: block; width: 100%; height: 100%; object-fit: cover; transition: transform 0.35s ease; }
.tile:hover img { transform: scale(1.04); }
.tile-tag {
  position: absolute; left: 8px; bottom: 8px; padding: 2px 7px; border-radius: 6px;
  background: rgba(8, 28, 44, 0.62); color: #fff; font-size: 11px; letter-spacing: 0.02em;
}
@media (max-width: 640px) { .wall { grid-template-columns: repeat(auto-fill, minmax(128px, 1fr)); gap: 8px; } }
</style>
