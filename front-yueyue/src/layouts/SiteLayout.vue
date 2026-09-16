<script setup lang="ts">
// 全站骨架:毛玻璃顶栏(logo + 五导航 + 四季点 + 用户菜单) + 内容 + 页脚。
// 顶栏 fixed,内容从 64px 起;移动端导航横向滚动,不藏进汉堡(六项放得下)。
import { useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { useAuthStore } from '@/stores/auth'
import { asset } from '@/stores/season'
import SeasonDots from '@/components/SeasonDots.vue'

const router = useRouter()
const auth = useAuthStore()

const NAVS = [
  { to: '/', label: '首页', exact: true },
  { to: '/notes', label: '笔记' },
  { to: '/projects', label: '项目' },
  { to: '/videos', label: '视频' },
  { to: '/code', label: '代码' },
]

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
    <header class="site-header">
      <router-link to="/" class="brand" exact-active-class="on">
        <img :src="asset('logo')" alt="月畔小站" />
        <span class="brand-text">
          <strong>月畔小站</strong>
          <em>yueyue · coast</em>
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

    <main class="site-body">
      <router-view />
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
  height: 64px;
  display: flex; align-items: center; gap: 24px;
  padding: 0 clamp(14px, 4vw, 40px);
  background: color-mix(in srgb, var(--card) 72%, transparent);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--line);
}

.brand { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.brand img { width: 38px; height: 38px; border-radius: 50%; object-fit: cover; }
.brand-text { display: flex; flex-direction: column; line-height: 1.15; }
.brand-text strong { font-size: 16px; color: var(--ink); letter-spacing: 0.08em; }
.brand-text em {
  font-style: normal; font-size: 9.5px; letter-spacing: 0.3em;
  text-transform: uppercase; color: var(--sea-deep);
}

.nav { display: flex; gap: 4px; overflow-x: auto; flex: 1; }
.nav a {
  padding: 7px 14px; border-radius: 999px;
  font-size: 15px; color: var(--ink-soft); white-space: nowrap;
  transition: background 0.2s, color 0.2s;
}
.nav a:hover { background: var(--cloud); color: var(--ink); }
.nav a.on { background: var(--sea-mid); color: #fff; }

.header-right { display: flex; align-items: center; gap: 18px; flex-shrink: 0; }

.user-chip {
  display: flex; align-items: center; gap: 7px;
  border: 1px solid var(--line); border-radius: 999px;
  background: var(--card); color: var(--ink);
  padding: 6px 14px; font-size: 14px; cursor: pointer;
  font-family: inherit;
}
.lock-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--sea-deep); }
.lock-dot.open { background: var(--sand); box-shadow: 0 0 6px var(--private-warm); }

.site-body { flex: 1; padding-top: 64px; }

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
