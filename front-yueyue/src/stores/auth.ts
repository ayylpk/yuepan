/** 登录态 store:数据真源在服务端 session,这里只是前端视图缓存。 */
import { defineStore } from 'pinia'
import { http } from '@/api/http'
import type { MeInfo } from '@/api/types'

// 开发旁路:后端 login 还没实现时,.env.development 设 VITE_AUTH_OFFLINE=true
// 即视为已登录(假用户),前端页面可以脱离后端继续开发/联调;上线/联调登录时关掉。
const OFFLINE = import.meta.env.VITE_AUTH_OFFLINE === 'true'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    loaded: false, // 首帧前问过一次 /auth/me 才置 true,路由闸门等它
    username: '',
    private: false,
  }),
  getters: {
    loggedIn: (s) => !!s.username,
  },
  actions: {
    async ensureLoaded() {
      if (!this.loaded) await this.refresh()
    },
    async refresh() {
      if (OFFLINE) {
        console.warn('[auth] VITE_AUTH_OFFLINE=true,登录校验已旁路(仅限开发)')
        this.username = '月畔(dev)'
        this.private = true
        this.loaded = true
        return
      }
      const me = await http.get<MeInfo>('/api/auth/me')
      this.username = me.logged_in ? (me.username ?? '') : ''
      this.private = !!me.private
      this.loaded = true
    },
    async login(username: string, password: string) {
      await http.post('/api/auth/login', { username, password })
      await this.refresh()
    },
    async logout() {
      await http.post('/api/auth/logout')
      await this.refresh()
    },
    async unlock(password: string) {
      await http.post('/api/auth/private/unlock', { password })
      await this.refresh()
    },
    async lock() {
      await http.post('/api/auth/private/lock')
      await this.refresh()
    },
  },
})
