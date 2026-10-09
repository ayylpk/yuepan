<script setup lang="ts">
// 站内导航抽屉(10/09 重塑新增)。
// 顶栏瘦到 56px 之后,6 个栏目收在这里;桌面与移动共用同一个组件,
// 只靠宽度与顶部那枚汉堡按钮区分——不维护两套导航,就不会两套行为不一致。
// 关闭动线三条:点遮罩 / Esc / 路由变化(选中即任务完成),另给 Ctrl(⌘)+K 唤起。
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { asset } from '@/stores/season'

const open = defineModel<boolean>({ default: false })
const route = useRoute()
const auth = useAuthStore()

const NAVS = [
  { to: '/', label: '首页', en: 'home', exact: true },
  { to: '/notes', label: '笔记', en: 'notes' },
  { to: '/projects', label: '项目', en: 'projects' },
  { to: '/photos', label: '照片', en: 'photos' },
  { to: '/files', label: '资料', en: 'files' },
  { to: '/code', label: '代码', en: 'code' },
]

function isOn(n: { to: string; exact?: boolean }) {
  return n.exact ? route.path === n.to : route.path.startsWith(n.to)
}

// 路由一变就收起:选中即闭环,不指望用户再点一次遮罩
watch(() => route.fullPath, () => { open.value = false })

// 打开时锁body滚动 + 把焦点送进抽屉;关闭时把锁还回去(卸载也要还,否则整站滚不动)
const closeRef = ref<HTMLButtonElement | null>(null)
function lockScroll(v: boolean) {
  document.body.style.overflow = v ? 'hidden' : ''
}
watch(open, (v) => {
  lockScroll(v)
  if (v) nextTick(() => closeRef.value?.focus())
})
onBeforeUnmount(() => lockScroll(false))

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && open.value) open.value = false
}
window.addEventListener('keydown', onKey)
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

const caveOn = computed(() => auth.private)
</script>

<template>
  <div class="drawer-root" :class="{ open }" :inert="!open" :aria-hidden="!open">
    <div class="drawer-scrim" @click="open = false" />

    <aside class="nav-drawer" role="dialog" aria-modal="true" aria-label="站内导航">
      <header class="drawer-head">
        <img :src="asset('logo')" alt="" />
        <span class="drawer-brand">
          <strong>月畔小站</strong>
          <em>yueyue · a private coast</em>
        </span>
        <button ref="closeRef" class="drawer-x" type="button" aria-label="关闭导航" @click="open = false">
          <i /><i />
        </button>
      </header>

      <nav class="drawer-nav">
        <router-link
          v-for="(n, i) in NAVS" :key="n.to" :to="n.to"
          class="nav-item" :class="{ on: isOn(n) }" :style="{ '--i': i }"
        >
          <span class="idx">{{ String(i + 1).padStart(2, '0') }}</span>
          <span class="zh">{{ n.label }}</span>
          <em>{{ n.en }}</em>
        </router-link>
      </nav>

      <footer class="drawer-foot">
        <router-link to="/private" class="cave-link">
          <span class="lock-dot" :class="{ open: caveOn }" />
          隐私小屋
          <em>{{ caveOn ? '灯亮着' : '锁着' }}</em>
        </router-link>
        <p class="drawer-tip">Ctrl / ⌘ + K 随时唤出</p>
      </footer>
    </aside>
  </div>
</template>

<style scoped>
.drawer-scrim {
  position: fixed; inset: 0; z-index: 300;
  background: rgba(6, 24, 38, 0.42);
  opacity: 0; visibility: hidden;
  transition: opacity 0.28s ease, visibility 0s linear 0.28s;
}
.nav-drawer {
  position: fixed; top: 0; left: 0; bottom: 0; z-index: 301;
  width: min(320px, 84vw);
  display: flex; flex-direction: column;
  background: var(--card);
  border-right: 1px solid var(--line);
  box-shadow: 0 24px 70px -24px rgba(8, 40, 66, 0.5);
  /* 与登录卡浮入同一条曲线:抽屉和登录卡是一家人,手感要接得上。
     visibility 那一档带延迟:滑出动画走完才真正藏起来(否则收起瞬间就消失)。
     配合模板上的 inert,收起后抽屉不进 Tab 序列、不进无障碍树 */
  visibility: hidden;
  transform: translateX(-102%);
  transition: transform 0.3s cubic-bezier(0.22, 0.61, 0.36, 1), visibility 0s linear 0.3s;
}
.open .drawer-scrim { opacity: 1; visibility: visible; transition: opacity 0.28s ease, visibility 0s; }
.open .nav-drawer { transform: none; visibility: visible; transition: transform 0.3s cubic-bezier(0.22, 0.61, 0.36, 1), visibility 0s; }

.drawer-head {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 14px 12px; border-bottom: 1px solid var(--line);
}
.drawer-head img { width: 32px; height: 32px; border-radius: 50%; object-fit: cover; flex: none; }
.drawer-brand { display: flex; flex-direction: column; line-height: 1.2; min-width: 0; }
.drawer-brand strong { font-size: 15px; color: var(--ink); letter-spacing: 0.08em; }
.drawer-brand em {
  font-style: italic; font-family: var(--font-serif);
  font-size: 10.5px; letter-spacing: 0.04em; color: var(--ink-soft);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
/* 关闭键:两笔划的 ×,不用字符,免得各平台字形不一样 */
.drawer-x {
  margin-left: auto; flex: none;
  position: relative; width: 32px; height: 32px;
  border: 1px solid var(--line); border-radius: 9px;
  background: none; cursor: pointer;
  transition: background-color 0.18s, border-color 0.18s;
}
.drawer-x i {
  position: absolute; left: 9px; top: 15px; width: 14px; height: 1.5px;
  background: var(--ink-soft); border-radius: 2px;
}
.drawer-x i:first-child { transform: rotate(45deg); }
.drawer-x i:last-child { transform: rotate(-45deg); }
.drawer-x:hover { background: var(--cloud); border-color: var(--card-line); }

.drawer-nav { flex: 1; overflow: auto; padding: 10px 12px; display: flex; flex-direction: column; gap: 2px; }
.nav-item {
  display: flex; align-items: baseline; gap: 10px;
  padding: 11px 12px; border-radius: 10px;
  color: var(--ink); transition: background-color 0.18s, color 0.18s;
}
.nav-item .idx { font-family: var(--font-mono); font-size: 11px; color: var(--ink-soft); flex: none; }
.nav-item .zh { font-size: 15px; letter-spacing: 0.08em; }
.nav-item em {
  margin-left: auto; font-style: italic; font-family: var(--font-serif);
  font-size: 11.5px; color: var(--ink-soft);
}
.nav-item:hover { background: var(--cloud); }
.nav-item.on { background: var(--brand); color: #fff; }
.nav-item.on .idx, .nav-item.on em { color: rgba(255, 255, 255, 0.8); }
/* 抽屉滑出时条目错峰跟上(复用全局 rise-in),让"打开"这件事有收尾 */
.open .nav-item {
  animation: rise-in 0.4s cubic-bezier(0.22, 0.61, 0.36, 1) backwards;
  animation-delay: calc(70ms + var(--i, 0) * 40ms);
}

.drawer-foot { padding: 12px; border-top: 1px solid var(--line); }
.cave-link {
  display: flex; align-items: center; gap: 9px;
  padding: 11px 12px; border-radius: 10px; color: var(--ink);
  background: color-mix(in srgb, var(--private-warm) 14%, transparent);
  transition: background-color 0.2s ease;
}
.cave-link:hover { background: color-mix(in srgb, var(--private-warm) 24%, transparent); }
.cave-link em { margin-left: auto; font-style: normal; font-size: 12px; color: var(--ink-soft); }
.lock-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--sea-deep); flex: none; }
.lock-dot.open { background: var(--sand); box-shadow: 0 0 7px var(--private-warm); }
.drawer-tip { margin: 10px 2px 0; font-size: 11.5px; color: var(--ink-soft); letter-spacing: 0.04em; }
</style>
