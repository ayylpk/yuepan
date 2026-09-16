<script setup lang="ts">
// 登录页:全屏海湾图 + 右下方玻璃登录卡。
// 登录成功跳 redirect 参数(路由闸门塞进来的),默认回首页。
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { useAuthStore } from '@/stores/auth'
import { asset } from '@/stores/season'
import { ApiError } from '@/api/http'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const form = reactive({ username: 'admin', password: '' })
const loading = ref(false)

async function submit() {
  if (!form.username || !form.password) {
    MessagePlugin.warning('先填上用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    MessagePlugin.success('欢迎回到月畔')
    router.replace(String(route.query.redirect || '/'))
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '登录失败,检查后端起没起')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login" :style="{ backgroundImage: `url(${asset('login')})` }">
    <div class="login-card glass-card">
      <img class="login-logo" :src="asset('logo')" alt="logo" />
      <h1>月畔小站</h1>
      <p class="eyebrow">yueyue · private coast</p>
      <form class="login-form" @submit.prevent="submit">
        <t-input v-model="form.username" size="large" placeholder="用户名" clearable />
        <t-input
          v-model="form.password" size="large" type="password"
          placeholder="密码" :autofocus="true" @enter="submit"
        />
        <t-button theme="primary" size="large" block :loading="loading" type="submit">
          推门进屋
        </t-button>
      </form>
      <p class="login-tip">默认账号 admin / 123456,登录后记得在设置里改</p>
    </div>
  </div>
</template>

<style scoped>
.login {
  min-height: 100vh;
  display: flex; align-items: center; justify-content: flex-end;
  padding: clamp(16px, 6vw, 88px);
  background: linear-gradient(160deg, var(--sky), var(--sea-mid));
  background-size: cover;
  background-position: center;
}
.login-card {
  width: min(380px, 92vw);
  padding: 36px 32px 28px;
  text-align: center;
}
.login-logo { width: 64px; height: 64px; border-radius: 50%; object-fit: cover; }
.login-card h1 { margin: 10px 0 2px; font-size: 26px; letter-spacing: 0.12em; color: var(--ink); }
.login-form { display: flex; flex-direction: column; gap: 14px; margin-top: 22px; }
.login-tip { margin-top: 18px; font-size: 12px; color: var(--ink-soft); }

@media (max-width: 720px) {
  .login { justify-content: center; }
}
</style>
