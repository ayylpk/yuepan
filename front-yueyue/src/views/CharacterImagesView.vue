<script setup lang="ts">
// 人物图片墙(10/20):/characters/:id/images
// 详情页把"批量图片"从直接铺开改成「查看 / 上传」两个按钮,全部图片在这里看。
// 与详情页口径一致:只展示图集(不含左侧那张独立肖像)。
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http } from '@/api/http'
import type { CharacterProfile, CharacterImage } from '@/api/types'
import ImageLightbox from '@/components/ImageLightbox.vue'

const route = useRoute()
const router = useRouter()
const characterId = computed(() => Number(route.params.id))

const row = ref<CharacterProfile | null>(null)
const loading = ref(true)
const index = ref<number | null>(null)

const images = computed<CharacterImage[]>(() =>
  (row.value?.images ?? []).filter(i => i.id !== row.value?.cover_image_id),
)

async function load() {
  loading.value = true
  try {
    row.value = await http.get<CharacterProfile>(`/api/characters/${characterId.value}`)
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '加载失败')
    router.replace('/characters')
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
onMounted(load)
watch(() => route.params.id, load)
</script>
<template>
  <div class="site-main wall-page">
    <t-loading :loading="loading">
      <template v-if="row">
        <div class="wall-top">
          <header class="page-head">
            <h2>{{ row.name }} · 图片</h2>
            <p class="meta"><span>{{ images.length }} 张</span><span v-if="row.subtitle">{{ row.subtitle }}</span></p>
          </header>
          <div class="actions">
            <t-button variant="text" @click="router.push(`/characters/${characterId}`)">回详情</t-button>
          </div>
        </div>

        <div v-if="!images.length" class="empty">还没有图片，回详情页批量上传。</div>
        <div v-else class="wall">
          <button v-for="(image, i) in images" :key="image.id" class="tile" type="button" :aria-label="`查看：${image.name}`" @click="open(i)">
            <img :src="image.url" :alt="image.name" loading="lazy" />
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
.meta { margin: 8px 0 0; display: flex; gap: 12px; flex-wrap: wrap; font-size: 13px; color: var(--ink-soft); }
.actions { display: flex; gap: 6px; flex-wrap: wrap; }
.empty { padding: 48px 0; color: var(--ink-soft); }
.wall { display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(168px, 1fr)); }
.tile {
  padding: 0; overflow: hidden; cursor: zoom-in;
  aspect-ratio: 4 / 3; border: 1px solid var(--line); border-radius: 10px; background: var(--cloud);
}
.tile img { display: block; width: 100%; height: 100%; object-fit: cover; transition: transform 0.35s ease; }
.tile:hover img { transform: scale(1.04); }
@media (max-width: 640px) { .wall { grid-template-columns: repeat(auto-fill, minmax(128px, 1fr)); gap: 8px; } }
</style>
