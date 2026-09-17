<script setup lang="ts">
// 全屏季节舞台(取代 PageHero 的"裁图横幅"):四季图当每页真正的背景。
// 结构三层各管一件事,互不抢 transform:
//   .stage__bg    入场编排的 1.5s 缓推(每次进页演一遍)
//   .stage__shift 滚动视差(背景以 ~0.18 倍速滞后,rAF 节流;幅度=溢出量,克制着来)
//   .stage__img×2 双层交叉溶解(换季 src 变化时新图预载→旧层淡出,硬切绝迹)
// 标题锁版 = 楷体大字 + Georgia 斜体伴行 + 可选一句话,左下浮动,错峰入场。
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  img: string        // asset() 解析好的 URL
  title: string      // 楷体主标
  en?: string        // 衬线斜体伴行,如 "notes · a private coast"
  line?: string      // 主标下的一小句话(首页用)
  pos?: string       // object-position 按图构图微调(如 code 图安静区偏右)
  hint?: boolean     // 底部"往下滚"的潮线箭头(首页船坞卡要它就让位)
}>(), { pos: 'center', hint: true })

// ---- 双层交叉溶解 ----
const layers = ref([
  { src: props.img, on: true },
  { src: '', on: false },
])
const cur = ref(0)

watch(() => props.img, (next) => {
  if (!next || next === layers.value[cur.value].src) return
  const nxt = 1 - cur.value
  layers.value[nxt].src = next
  const pre = new Image()
  const reveal = () => {
    layers.value[nxt].on = true
    layers.value[cur.value].on = false
    cur.value = nxt
  }
  pre.onload = reveal
  pre.onerror = reveal // 加载失败也得换过去,旧图留着更误导
  pre.src = next
})

// ---- 视差:只在下落窗口内累计,舞台滚出视口即归零 ----
const stageEl = ref<HTMLElement>()
const shift = ref('')
let raf = 0
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
function onScroll() {
  if (raf) return
  raf = requestAnimationFrame(() => {
    raf = 0
    const el = stageEl.value
    if (!el) return
    const y = Math.min(window.scrollY, el.offsetHeight)
    // 0.18 而非旧 0.35:视差是"意思一下",幅度过大就得垫更高的溢出层,图跟着被放大变糊
    shift.value = `translate3d(0, ${(y * 0.18).toFixed(1)}px, 0)`
  })
}
onMounted(() => {
  if (reduceMotion) return
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
})
onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  if (raf) cancelAnimationFrame(raf)
})

const shiftStyle = computed(() => ({ transform: shift.value }))
</script>

<template>
  <header ref="stageEl" class="stage" :style="{ '--hero-pos': pos }">
    <div class="stage__bg" aria-hidden="true">
      <div class="stage__shift" :style="shiftStyle">
        <img
          v-for="(l, i) in layers" :key="i"
          v-show="l.src" :src="l.src"
          class="stage__img" :class="{ on: l.on }" alt=""
        />
      </div>
    </div>
    <div class="stage__scrim" aria-hidden="true" />

    <div class="stage__copy">
      <h1>{{ title }}</h1>
      <p v-if="en" class="stage__en">{{ en }}</p>
      <p v-if="line" class="stage__line">{{ line }}</p>
      <slot />
    </div>

    <div v-if="hint" class="stage__hint" aria-hidden="true"><span /></div>
  </header>
</template>

<style scoped>
.stage {
  position: relative;
  min-height: 100svh;
  display: flex; align-items: flex-end;
  overflow: hidden;
  isolation: isolate;
  /* 图未就位/缺图时的季节色兜底(和旧 PageHero 同一思路) */
  background: linear-gradient(165deg, var(--sky) 8%, var(--sea-mid));
}

.stage__bg {
  position: absolute; left: 0; right: 0; top: 0; bottom: 0; z-index: -2;
  animation: stage-zoom 1.5s ease-out backwards;
}
/* 溢出量按视差最大行程(0.18)刚好够盖:层每多垫 10%,cover 的图就多放大 10%——糊的元凶之一 */
.stage__shift {
  position: absolute; left: 0; right: 0; top: -6%; height: 112%;
  will-change: transform;
}
.stage__img {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  object-fit: cover; object-position: var(--hero-pos);
  opacity: 0; transition: opacity 0.7s ease;
}
.stage__img.on { opacity: 1; }
@keyframes stage-zoom {
  from { transform: scale(1.02); }
  to   { transform: scale(1); }
}

/* 压字渐变:底部深渐层保标题可读,顶部一抹薄影保透明顶栏可读 */
.stage__scrim {
  position: absolute; inset: 0; z-index: -1;
  background:
    linear-gradient(to bottom, rgba(6, 30, 48, 0.30), transparent 20%),
    linear-gradient(to top, var(--scrim), transparent 46%);
}

.stage__copy {
  position: relative; z-index: 1;
  width: 100%;
  padding: 0 clamp(20px, 6vw, 72px) clamp(64px, 11vh, 110px);
}
.stage__copy h1 {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 400;
  font-size: clamp(42px, 6.4vw, 72px);
  letter-spacing: 0.12em;
  color: #fff;
  text-shadow: 0 2px 22px rgba(8, 40, 66, 0.55);
  animation: copy-rise 0.8s 0.15s cubic-bezier(0.22, 0.61, 0.36, 1) backwards;
}
.stage__en {
  margin: 8px 0 0;
  font-family: var(--font-serif); font-style: italic;
  font-size: clamp(14px, 1.6vw, 18px); letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.9);
  text-shadow: 0 1px 10px rgba(8, 40, 66, 0.5);
  animation: copy-rise 0.8s 0.3s cubic-bezier(0.22, 0.61, 0.36, 1) backwards;
}
.stage__line {
  margin: 12px 0 0; font-size: 14.5px; color: rgba(255, 255, 255, 0.86);
  text-shadow: 0 1px 10px rgba(8, 40, 66, 0.5);
  animation: copy-rise 0.8s 0.44s cubic-bezier(0.22, 0.61, 0.36, 1) backwards;
}
/* slot 内容(如首页动态一句话)的入场由调用方自己引用全局 copy-rise keyframes */

/* 潮线箭头:两笔画的 V,呼吸式下探,提示下面还有内容 */
.stage__hint {
  position: absolute; left: 50%; bottom: 20px; z-index: 1;
  animation: hint-bob 2.2s ease-in-out infinite;
}
.stage__hint span {
  display: block; width: 13px; height: 13px;
  border-right: 2px solid rgba(255, 255, 255, 0.85);
  border-bottom: 2px solid rgba(255, 255, 255, 0.85);
  transform: rotate(45deg);
}
@keyframes hint-bob {
  0%, 100% { transform: translate(-50%, 0); opacity: 0.5; }
  50%      { transform: translate(-50%, 7px); opacity: 1; }
}
</style>
