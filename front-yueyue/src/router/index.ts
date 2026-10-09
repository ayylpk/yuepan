/** 路由表 + 登录闸门 + 小屋自动落锁。
 *  Java 视角:beforeEach 就是一个全局 Filter,public 路径直接放行,
 *  其余先问 /auth/me(只在首帧问一次),没登录统一轰去 /login?redirect=。
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { public: true, title: '登录 · 月畔小站' } },
    {
      path: '/',
      component: () => import('@/layouts/SiteLayout.vue'),
      // meta.shell 决定页面用哪套骨架(10/09 重塑,取代原来的 hero 布尔值):
      //   stage  = 全屏季节舞台,内容压在地板带上(首页/照片/小屋,观赏型)
      //   banner = 260px 窄横幅 + 内容紧接其后(笔记/项目/资料/代码,工具型)
      //   plain  = 无图,纯标题区(设置/笔记详情)
      // 判据只有一条:这一页是来"看"的还是来"用"的。
      children: [
        { path: '', name: 'home', component: () => import('@/views/HomeView.vue'), meta: { title: '月畔小站', shell: 'stage' } },
        { path: 'notes', name: 'notes', component: () => import('@/views/NotesView.vue'), meta: { title: '笔记 · 月畔小站', shell: 'banner' } },
        { path: 'notes/new', name: 'note-new', component: () => import('@/views/NoteView.vue'), meta: { title: '新笔记 · 月畔小站', shell: 'plain' } },
        { path: 'notes/:id', name: 'note', component: () => import('@/views/NoteView.vue'), meta: { title: '笔记 · 月畔小站', shell: 'plain' } },
        { path: 'projects', name: 'projects', component: () => import('@/views/ProjectsView.vue'), meta: { title: '项目 · 月畔小站', shell: 'banner' } },
        { path: 'photos', name: 'photos', component: () => import('@/views/PhotosView.vue'), meta: { title: '照片 · 月畔小站', shell: 'stage' } },
        { path: 'files', name: 'files', component: () => import('@/views/FilesView.vue'), meta: { title: '资料 · 月畔小站', shell: 'banner' } },
        { path: 'code', name: 'code', component: () => import('@/views/CodeView.vue'), meta: { title: '代码 · 月畔小站', shell: 'banner' } },
        { path: 'private', name: 'private', component: () => import('@/views/PrivateView.vue'), meta: { title: '小屋 · 月畔小站', shell: 'stage' } },
        { path: 'settings', name: 'settings', component: () => import('@/views/SettingsView.vue'), meta: { title: '设置 · 月畔小站', shell: 'plain' } },
      ],
    },
    { path: '/:pathMatch(.*)*', name: 'notfound', component: () => import('@/views/NotFoundView.vue'), meta: { public: true, title: '404 · 月畔小站' } },
  ],
  // 切页重置滚动位置,浏览器前进/后退则还原(重塑批1:之前没有这条,A→B 会带着 A 的滚动深度进场)。
  // 延迟 200ms 再置顶:页转场是 out-in,旧页淡出占前 160ms,立刻 reset 会让淡出中的旧页跳顶。
  scrollBehavior(_to, _from, saved) {
    if (saved) return saved
    return new Promise((resolve) => setTimeout(() => resolve({ top: 0 }), 200))
  },
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    // 已登录还去登录页 → 直接回首页
    if (to.name === 'login') {
      await auth.ensureLoaded()
      if (auth.loggedIn) return { name: 'home' }
    }
    return true
  }
  await auth.ensureLoaded()
  if (!auth.loggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})

// 9/26 验收二轮:"灯只在屋里亮" —— 离开小屋动线自动落锁,不再依赖手动按钮。
// 小屋驻点 = /private 本身 + 带 ?from=cave 的笔记页(小屋"去编辑"的延伸,不算离屋)。
// 挂在 afterEach 而不是 PrivateView 卸载钩子:小屋→编辑页的跳转同样会卸载组件,挂卸载会误锁。
// 非 public 路由 beforeEach 已 ensureLoaded,走到这里 auth.private 反映的是服务端真值;
// 刷新落在屋外页面同样触发补锁(beforeEach 先解析完才进 afterEach)。
router.afterEach((to) => {
  if (to.meta.title) document.title = String(to.meta.title)
  const isCaveStop = to.name === 'private' || String(to.query.from ?? '') === 'cave'
  if (!isCaveStop) {
    const auth = useAuthStore()
    if (auth.private) auth.lock().catch(() => {})
  }
})

export default router
