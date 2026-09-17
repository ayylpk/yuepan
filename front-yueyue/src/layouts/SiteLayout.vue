<script setup lang="ts">
// 全站骨架:两态顶栏 + 内容 + 页脚。
//  - 顶栏:舞台页(route.meta.hero)第一屏透明压图、白字,滚过 40px 固化成毛玻璃;
//    非舞台页(设置/笔记详情)始终毛玻璃。
//  - 壳内换页的转场挂这层的内层 router-view(App.vue 只管 登录/404 ↔ 壳)。
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { useAuthStore } from '@/stores/auth'
import { asset } from '@/stores/season'
import SeasonDots from '@/components/SeasonDots.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const NAVS = [
  { to: '/', label: '首页', exact: true },
  { to: '/notes', label: '笔记' },
  { to: '/projects', label: '项目' },
  { to: '/photos', label: '照片' },
  { to: '/files', label: '资料' },
  { to: '/code', label: '代码' },
]

// ---- 顶栏两态:滚动过阈值就固化(passive 监听,只做布尔翻转不重排) ----
const scrolled = ref(false)
function onScroll() { scrolled.value = window.scrollY > 40 }
onMounted(() => {
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
})
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))
const overHero = computed(() => !!route.meta.hero && !scrolled.value)

// 内层转场的 key:按路由名 + 笔记 id 重挂(同页查询参数变化不重挂不闪)
function pageKey(r: typeof route) {
  return `${String(r.name ?? r.path)}${r.params.id ? '/' + String(r.params.id) : ''}`
}

async function onUserCommand(cmd: string) {
  if (cmd === 'private') router.push('/private')
  else if (cmd === 'settings') router.push('/settings')
  else if (cmd === 'logout') {
    await auth.logout()
    MessagePlugin.success('已登出,海面平静')
    router.push('/login')
  }
}
</script>

<template>
  <div class="site">
    <header class="site-header" :class="{ 'over-hero': overHero }">
      <router-link to="/" class="brand" exact-active-class="on">
        <img :src="asset('logo')" alt="月畔小站" />
        <span class="brand-text">
          <strong>月畔小站</strong>
          <em>yueyue · a private coast</em>
        </span>
      </router-link>

      <nav class="nav">
        <router-link
          v-for="n in NAVS" :key="n.to" :to="n.to"
          :exact-active-class="n.exact ? 'on' : ''"
          :active-class="n.exact ? '' : 'on'"
        >{{ n.label }}</router-link>
      </nav>

      <div class="header-right">
        <SeasonDots />
        <t-dropdown :options="[
          { content: '隐私小屋', value: 'private' },
          { content: '设置', value: 'settings' },
          { content: '退出登录', value: 'logout' },
        ]" @click="(item: any) => onUserCommand(item.value)">
          <button class="user-chip" :title="auth.private ? '隐私空间已解锁' : '隐私空间已上锁'">
            <span class="lock-dot" :class="{ open: auth.private }" />
            {{ auth.username }}
          </button>
        </t-dropdown>
      </div>
    </header>

    <main class="site-body" :class="{ 'no-pad': route.meta.hero }">
      <router-view v-slot="{ Component }">
        <transition name="route" mode="out-in">
          <component :is="Component" :key="pageKey(route)" />
        </transition>
      </router-view>
    </main>

    <footer class="site-footer">
      月畔小站 · 灯塔不灭<span v-if="auth.private" class="footer-private"> · 小屋灯亮着</span>
    </footer>
  </div>
</template>

<style scoped>
.site { min-height: 100vh; display: flex; flex-direction: column; }

.site-header {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  height: var(--header-h);
  display: flex; align-items: center; gap: 24px;
  padding: 0 clamp(14px, 4vw, 40px);
  background: color-mix(in srgb, var(--card) 72%, transparent);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--line);
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

/* ---------- 透明压图态:字全走白色系 + 阴影垫,图上的天空再亮也读得出 ---------- */
.over-hero {
  background: transparent;
  backdrop-filter: none;
  border-bottom-color: transparent;
}
.over-hero .brand-text strong { color: #fff; text-shadow: 0 1px 10px rgba(8, 40, 66, 0.5); }
.over-hero .brand-text em { color: rgba(255, 255, 255, 0.82); text-shadow: 0 1px 8px rgba(8, 40, 66, 0.5); }
.over-hero .brand img { box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.55), 0 2px 10px rgba(8, 40, 66, 0.35); }
.over-hero .nav a { color: rgba(255, 255, 255, 0.88); text-shadow: 0 1px 8px rgba(8, 40, 66, 0.45); }
.over-hero .nav a:hover { background: rgba(255, 255, 255, 0.14); color: #fff; }
.over-hero .nav a.on { background: rgba(255, 255, 255, 0.2); color: #fff; }
.over-hero .user-chip {
  background: rgba(10, 40, 60, 0.3);
  border-color: rgba(255, 255, 255, 0.35);
  color: #fff;
  backdrop-filter: blur(6px);
}

.brand { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.brand img { width: 38px; height: 38px; border-radius: 50%; object-fit: cover; }
.brand-text { display: flex; flex-direction: column; line-height: 1.15; }
.brand-text strong { font-size: 16px; color: var(--ink); letter-spacing: 0.08em; }
/* 品牌小字:旧 ALL-CAPS 宽字距撤了,换 Georgia 斜体伴行(书名页语气) */
.brand-text em {
  font-style: italic; font-size: 10.5px; letter-spacing: 0.04em;
  font-family: var(--font-serif); color: var(--ink-soft);
}

.nav { display: flex; gap: 4px; overflow-x: auto; flex: 1; }
.nav a {
  position: relative;
  padding: 7px 14px; border-radius: 999px;
  font-size: 15px; color: var(--ink-soft); white-space: nowrap;
  transition: background 0.2s, color 0.2s;
}
/* 悬停潮线:底衬一道细浪滑入 */
.nav a::after {
  content: ''; position: absolute; left: 14px; right: 14px; bottom: 3px;
  height: 2px; border-radius: 2px; background: currentColor; opacity: 0.7;
  transform: scaleX(0); transition: transform 0.25s ease;
}
.nav a:hover::after { transform: scaleX(1); }
.nav a.on::after { display: none; } /* 选中态已有底衬,不叠浪线 */
.nav a:hover { background: var(--cloud); color: var(--ink); }
.nav a.on { background: var(--sea-mid); color: #fff; }

.header-right { display: flex; align-items: center; gap: 18px; flex-shrink: 0; }

.user-chip {
  display: flex; align-items: center; gap: 7px;
  border: 1px solid var(--line); border-radius: 999px;
  background: var(--card); color: var(--ink);
  padding: 6px 14px; font-size: 14px; cursor: pointer;
  font-family: inherit;
  transition: background-color 0.3s, color 0.3s, border-color 0.3s;
}
.lock-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--sea-deep); }
.lock-dot.open { background: var(--sand); box-shadow: 0 0 6px var(--private-warm); }

.site-body { flex: 1; padding-top: var(--header-h); }
/* 舞台页:内容从 0 起,让背景图钻到透明顶栏底下 */
.site-body.no-pad { padding-top: 0; }

.site-footer {
  padding: 22px; text-align: center;
  font-size: 13px; letter-spacing: 0.15em; color: var(--ink-soft);
  border-top: 1px solid var(--line);
}
.footer-private { color: var(--private-warm); }

@media (max-width: 720px) {
  .brand-text { display: none; }
  .header-right { margin-left: auto; }
  .nav { flex: 0 1 auto; }
}
</style>
