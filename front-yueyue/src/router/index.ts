/** 路由表 + 登录闸门。
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
      children: [
        { path: '', name: 'home', component: () => import('@/views/HomeView.vue'), meta: { title: '月畔小站' } },
        { path: 'notes', name: 'notes', component: () => import('@/views/NotesView.vue'), meta: { title: '笔记 · 月畔小站' } },
        { path: 'notes/new', name: 'note-new', component: () => import('@/views/NoteView.vue'), meta: { title: '新笔记 · 月畔小站' } },
        { path: 'notes/:id', name: 'note', component: () => import('@/views/NoteView.vue'), meta: { title: '笔记 · 月畔小站' } },
        { path: 'projects', name: 'projects', component: () => import('@/views/ProjectsView.vue'), meta: { title: '项目 · 月畔小站' } },
        { path: 'videos', name: 'videos', component: () => import('@/views/VideosView.vue'), meta: { title: '视频 · 月畔小站' } },
        { path: 'code', name: 'code', component: () => import('@/views/CodeView.vue'), meta: { title: '代码 · 月畔小站' } },
        { path: 'private', name: 'private', component: () => import('@/views/PrivateView.vue'), meta: { title: '小屋 · 月畔小站' } },
        { path: 'settings', name: 'settings', component: () => import('@/views/SettingsView.vue'), meta: { title: '设置 · 月畔小站' } },
      ],
    },
    { path: '/:pathMatch(.*)*', name: 'notfound', component: () => import('@/views/NotFoundView.vue'), meta: { public: true, title: '404 · 月畔小站' } },
  ],
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

router.afterEach((to) => {
  if (to.meta.title) document.title = String(to.meta.title)
})

export default router
