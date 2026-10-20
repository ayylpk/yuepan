<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'

// hasPrev/hasNext 是可选的:不传就是原来的单图预览(照片页/资料页照旧)。
// 图片墙页面传进来后可以用左右方向键翻页。
const props = defineProps<{
  src: string
  alt?: string
  caption?: string
  hasPrev?: boolean
  hasNext?: boolean
}>()

const emit = defineEmits<{ close: []; prev: []; next: [] }>()

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
  else if (event.key === 'ArrowLeft' && props.hasPrev) emit('prev')
  else if (event.key === 'ArrowRight' && props.hasNext) emit('next')
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div class="image-lightbox" role="dialog" aria-modal="true" aria-label="图片预览" @click="emit('close')">
      <button class="image-lightbox__close" type="button" aria-label="关闭图片预览" @click="emit('close')">×</button>
      <button v-if="hasPrev" class="image-lightbox__nav image-lightbox__nav--prev" type="button" aria-label="上一张" @click.stop="emit('prev')">‹</button>
      <figure class="image-lightbox__figure" @click.stop>
        <img class="image-lightbox__image" :src="src" :alt="alt || '图片预览'" />
        <figcaption v-if="caption" class="image-lightbox__caption">{{ caption }}</figcaption>
      </figure>
      <button v-if="hasNext" class="image-lightbox__nav image-lightbox__nav--next" type="button" aria-label="下一张" @click.stop="emit('next')">›</button>
    </div>
  </Teleport>
</template>

<style scoped>
.image-lightbox {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 24px 36px;
  background: rgba(6, 24, 38, 0.86);
  backdrop-filter: blur(7px);
  cursor: zoom-out;
  animation: image-lightbox-in 0.2s ease both;
}
.image-lightbox__figure { max-width: 94vw; max-height: 90vh; margin: 0; text-align: center; }
.image-lightbox__image { display: block; max-width: 94vw; max-height: 82vh; object-fit: contain; border-radius: 12px; box-shadow: 0 30px 80px -20px rgba(0, 0, 0, 0.72); }
.image-lightbox__caption { margin-top: 12px; color: rgba(230, 244, 252, 0.88); font-size: 13px; }
.image-lightbox__close { position: fixed; top: 14px; right: 18px; border: 0; background: transparent; color: #fff; font-size: 34px; line-height: 1; cursor: pointer; }
.image-lightbox__nav {
  position: fixed; top: 50%; transform: translateY(-50%);
  width: 48px; height: 84px; border: 0; border-radius: 10px;
  background: rgba(255, 255, 255, 0.08); color: #fff;
  font-size: 40px; line-height: 1; cursor: pointer;
  transition: background 0.2s ease;
}
.image-lightbox__nav:hover { background: rgba(255, 255, 255, 0.18); }
.image-lightbox__nav--prev { left: 14px; }
.image-lightbox__nav--next { right: 14px; }
@keyframes image-lightbox-in { from { opacity: 0; } to { opacity: 1; } }
</style>
