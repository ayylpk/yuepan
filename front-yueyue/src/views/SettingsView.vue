<script setup lang="ts">
// 设置页:改用户名 / 改主密码 / 改小屋解锁密码。
// 接口等后端 login.py 做好后自然接通(/api/auth/* 契约已在前端固化)。
import { reactive, ref } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import ProjectManager from '@/components/admin/ProjectManager.vue'
import TechManager from '@/components/admin/TechManager.vue'

const auth = useAuthStore()
const router = useRouter()

const pwd = reactive({ old: '', next: '', confirm: '' })
const name = reactive({ value: '', password: '' })
const priv = reactive({ old: '', next: '' })
const busy = ref('')

async function run(key: string, fn: () => Promise<void>) {
  busy.value = key
  try {
    await fn()
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '请求失败(后端 auth 接口还没实现?)')
  } finally {
    busy.value = ''
  }
}

function savePwd() {
  if (pwd.next.length < 6) return MessagePlugin.warning('新密码至少 6 位')
  if (pwd.next !== pwd.confirm) return MessagePlugin.warning('两次输入的新密码不一致')
  run('pwd', async () => {
    await http.post('/api/auth/password', { old_password: pwd.old, new_password: pwd.next })
    Object.assign(pwd, { old: '', next: '', confirm: '' })
    MessagePlugin.success('主密码已更新')
  })
}

function saveName() {
  if (!name.value.trim()) return MessagePlugin.warning('新用户名不能为空')
  run('name', async () => {
    await http.post('/api/auth/username', { new_username: name.value.trim(), password: name.password })
    await auth.refresh()
    Object.assign(name, { value: '', password: '' })
    MessagePlugin.success('用户名已更新')
  })
}

function savePriv() {
  if (priv.next.length < 6) return MessagePlugin.warning('新解锁密码至少 6 位')
  run('priv', async () => {
    await http.post('/api/auth/private/password', { old_password: priv.old, new_password: priv.next })
    Object.assign(priv, { old: '', next: '' })
    MessagePlugin.success('小屋锁芯已换')
  })
}

async function logout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="site-main settings">
    <header class="page-head">
      <h2>设置</h2>
      <p class="en">settings</p>
    </header>

    <div class="set-grid">
      <section class="glass-card set-card">
        <h2>账号</h2>
        <p class="now">当前用户:<strong>{{ auth.username }}</strong> · 小屋{{ auth.private ? '灯亮着' : '锁着' }}</p>
        <t-input v-model="name.value" placeholder="新用户名" />
        <t-input v-model="name.password" type="password" placeholder="当前密码(改名必验)" />
        <t-button theme="primary" variant="outline" :loading="busy === 'name'" @click="saveName">改用户名</t-button>
        <t-divider />
        <t-button variant="text" theme="danger" @click="logout">退出登录</t-button>
      </section>

      <section class="glass-card set-card">
        <h2>主密码</h2>
        <p class="now">整站大门的钥匙</p>
        <t-input v-model="pwd.old" type="password" placeholder="原密码" />
        <t-input v-model="pwd.next" type="password" placeholder="新密码(≥6位)" />
        <t-input v-model="pwd.confirm" type="password" placeholder="再输一遍新密码" />
        <t-button theme="primary" variant="outline" :loading="busy === 'pwd'" @click="savePwd">改主密码</t-button>
      </section>

      <section class="glass-card set-card">
        <h2>小屋解锁密码</h2>
        <p class="now">第二道锁的锁芯</p>
        <t-input v-model="priv.old" type="password" placeholder="原解锁密码" />
        <t-input v-model="priv.next" type="password" placeholder="新解锁密码(≥6位)" />
        <t-button theme="primary" variant="outline" :loading="busy === 'priv'" @click="savePriv">改解锁密码</t-button>
      </section>
    </div>

    <!-- 站点内容管理:本页在路由登录闸门之后,能站在这的就是自己人 -->
    <header class="page-head admin-title">
      <h2>站点管理</h2>
      <p class="en">admin</p>
    </header>
    <div class="admin-stack">
      <ProjectManager />
      <TechManager />
    </div>
  </div>
</template>

<style scoped>
.settings { padding-top: 36px; }
.set-grid { display: grid; gap: 18px; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
.admin-title { margin-top: 44px; }
.admin-stack { display: grid; gap: 18px; }
.set-card { padding: 22px 24px; display: flex; flex-direction: column; gap: 12px; align-items: flex-start; }
.set-card h2 { margin: 0; font-size: 17px; color: var(--ink); }
.now { margin: 0; font-size: 13px; color: var(--ink-soft); }
.set-card :deep(.t-input__wrap) { width: 100%; }
</style>
