<script setup lang="ts">
// 全站骨架(10/09 重塑):
//  - 顶栏只留四样:品牌 / 四季圆点 / 用户 / 汉堡。6 个栏目搬进 NavDrawer——
//    "栏目越多顶栏越挤"这个死结一次性解掉,顶栏高度也从 64 降到 56。
//  - 两态顶栏保留:stage 骨架(首页/照片/小屋)第一屏透明压图+白字,滚过 40px 固化;
//    banner / plain 骨架始终实底——它们的封面在顶栏下面,没有压图这回事。
//  - 壳内换页的转场挂这层的内层 router-view(App.vue 只管 登录/404 ↔ 壳)。
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { useAuthStore } from '@/stores/auth'
import { asset } from '@/stores/season'
import SeasonDots from '@/components/SeasonDots.vue'
import NavDrawer from '@/components/NavDrawer.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// 骨架声明见 router/index.ts。stage=全屏舞台 / banner=窄横幅 / plain=纯标题区
const shell = computed(() => String(route.meta.shell ?? 'plain'))
const drawerOpen = ref(false)

// ---- 顶栏两态:滚动过阈值就固化(passive 监听,只做布尔翻转不重排) ----
const scrolled = ref(false)
function onScroll() { scrolled.value = window.scrollY > 40 }
const overHero = computed(() => shell.value === 'stage' && !scrolled.value)

// ---- Ctrl / ⌘ + K 唤起导航:抽屉方案下桌面端少点一次鼠标的补偿 ----
function onHotkey(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    drawerOpen.value = true
  }
}
onMounted(() => {
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('keydown', onHotkey)
})
onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('keydown', onHotkey)
})

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

      <div class="header-right">
        <SeasonDots />
        <t-dropdown :options="[
          { content: '隐私小屋', value: 'private' },
          { content: '设置', value: 'settings' },
          { content: '退出登录', value: 'logout' },
        ]" @click="(item: any) => onUserCommand(item.value)">
          <button class="user-chip" :title="auth.private ? '隐私空间已解锁' : '隐私空间已上锁'">
            <span class="lock-dot" :class="{ open: auth.private }" />
            <span class="uname">{{ auth.username }}</span>
          </button>
        </t-dropdown>
        <button class="nav-toggle" type="button" aria-label="打开导航" title="导航(Ctrl/⌘ + K)" @click="drawerOpen = true">
          <i /><i /><i />
        </button>
      </div>
    </header>

    <main class="site-body" :class="{ 'no-pad': shell === 'stage' }">
      <router-view v-slot="{ Component }">
        <transition name="route" mode="out-in">
          <component :is="Component" :key="pageKey(route)" />
        </transition>
      </router-view>
    </main>

    <footer class="site-footer">
      月畔小站 · 灯塔不灭<span v-if="auth.private" class="footer-private"> · 小屋灯亮着</span>
    </footer>

    <NavDrawer v-model="drawerOpen" />
  </div>
</template>

<style scoped>
.site { min-height: 100vh; display: flex; flex-direction: column; }

.site-header {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  height: var(--header-h);
  display: flex; align-items: center; gap: 16px;
  padding: 0 clamp(14px, 4vw, 40px);
  background: color-mix(in srgb, var(--card) 78%, transparent);
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
.over-hero .user-chip {
  background: rgba(10, 40, 60, 0.3);
  border-color: rgba(255, 255, 255, 0.35);
  color: #fff;
  backdrop-filter: blur(6px);
}
.over-hero .nav-toggle { border-color: rgba(255, 255, 255, 0.4); }
.over-hero .nav-toggle i { background: #fff; }

.brand { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.brand img { width: 36px; height: 36px; border-radius: 50%; object-fit: cover; }
.brand-text { display: flex; flex-direction: column; line-height: 1.15; }
.brand-text strong { font-size: 15.5px; color: var(--ink); letter-spacing: 0.08em; }
/* 品牌小字:Georgia 斜体伴行(书名页语气) */
.brand-text em {
  font-style: italic; font-size: 10.5px; letter-spacing: 0.04em;
  font-family: var(--font-serif); color: var(--ink-soft);
}

.header-right { display: flex; align-items: center; gap: 14px; margin-left: auto; flex-shrink: 0; }

.user-chip {
  display: flex; align-items: center; gap: 7px;
  border: 1px solid var(--line); border-radius: 999px;
  background: var(--card); color: var(--ink);
  padding: 6px 13px; font-size: 14px; cursor: pointer;
  font-family: inherit;
  transition: background-color 0.3s, color 0.3s, border-color 0.3s;
}
.lock-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--sea-deep); flex: none; }
.lock-dot.open { background: var(--sand); box-shadow: 0 0 6px var(--private-warm); }

/* 汉堡:三笔划,不用字体图标(不引 webfont 是这站的既定纪律) */
.nav-toggle {
  width: 36px; height: 36px; flex: none;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;
  border: 1px solid var(--line); border-radius: 10px;
  background: var(--card); cursor: pointer;
  transition: background-color 0.22s ease, border-color 0.22s ease;
}
.nav-toggle i { display: block; width: 15px; height: 1.5px; border-radius: 2px; background: var(--ink-soft); }
.nav-toggle:hover { background: var(--cloud); border-color: var(--card-line); }
.nav-toggle:hover i { background: var(--ink); }

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
  .header-right { gap: 10px; }
  .uname { display: none; } /* 窄屏用户胶囊只留锁状态那枚点 */
  .user-chip { padding: 6px 10px; }
}
</style>
