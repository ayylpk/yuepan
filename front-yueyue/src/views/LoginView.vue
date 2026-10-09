<script setup lang="ts">
// 登录页(9/17 批4.2):全屏海湾图,初始画面只有图。
// 签名交互:滚轮下滑/向上拖动 → 登录卡从下方浮入居中;反方向 → 原路隐去。
// 拖拽、滚轮双向对称,触摸走 pointer 同源;Tab 聚焦也能掀帘。底部小箭头只做
// "卡还没出来"时的低调暗示,出现即退场。登录成功跳 redirect(闸门塞的),默认回首页。
import { nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
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
const revealed = ref(false)
const pwdRef = ref<{ focus: () => void } | null>(null)

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

// ---- 双向开关:滚轮累计下滚出现 / 上滚隐去 / 垂直拖动同义 / 键盘聚焦掀帘 ----
const FLIP = 70 // 触发阈值(累计 delta 或拖动像素)
let wheelAcc = 0
function onWheel(e: WheelEvent) {
  wheelAcc = Math.max(-140, Math.min(140, wheelAcc + e.deltaY))
  if (wheelAcc > FLIP) { setShown(true); wheelAcc = 0 }
  else if (wheelAcc < -FLIP) { setShown(false); wheelAcc = 0 }
}
let dragFromY: number | null = null
function onPointerDown(e: PointerEvent) { dragFromY = e.clientY }
function onPointerMove(e: PointerEvent) {
  if (dragFromY === null) return
  const dy = e.clientY - dragFromY
  if (dy < -FLIP * 0.7) { setShown(true); dragFromY = null } // 上提:内容跟上来
  else if (dy > FLIP * 0.7) { setShown(false); dragFromY = null } // 下拽:内容跟下去
}
function onPointerUp() { dragFromY = null }
function setShown(v: boolean) {
  if (revealed.value === v) return
  revealed.value = v
  // 出现动画走完再把光标送进密码框(不能用 autofocus:进页秒掀帘,交互就没了);
  // 隐去时若焦点还在卡内,visibility:hidden 会自动丢焦,不用我们操心
  if (v) nextTick(() => setTimeout(() => pwdRef.value?.focus(), 520))
}

onMounted(() => {
  window.addEventListener('wheel', onWheel, { passive: true })
  window.addEventListener('pointerdown', onPointerDown)
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
})
onBeforeUnmount(() => {
  window.removeEventListener('wheel', onWheel)
  window.removeEventListener('pointerdown', onPointerDown)
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
})
</script>

<template>
  <div class="full-stage login">
    <img v-img-fade class="full-stage__bg" :src="asset('login')" alt="" />
    <div class="full-stage__scrim" aria-hidden="true" />

    <div class="login-card glass-overlay" :class="{ shown: revealed }" @focusin="setShown(true)">
      <img class="login-logo" :src="asset('logo')" alt="logo" />
      <h1>月畔小站</h1>
      <p class="login-en">yueyue · a private coast</p>
      <form class="login-form" @submit.prevent="submit">
        <t-input v-model="form.username" size="large" placeholder="用户名" clearable />
        <t-input
          ref="pwdRef" v-model="form.password" size="large" type="password"
          placeholder="密码" @enter="submit"
        />
        <t-button theme="primary" size="large" block :loading="loading" type="submit">
          推门进屋
        </t-button>
      </form>
      <p class="login-tip">密码是你在后端设的那把。进屋后记得去设置里换</p>
    </div>

    <!-- 低调的暗示:小 chevron 慢呼吸,卡出现即退场(滚轮上滚还能收回去) -->
    <button
      class="login-cue" :class="{ gone: revealed }" type="button"
      aria-label="下滑或拖动显示登录表单" @click="setShown(true)"
    ><span /></button>
  </div>
</template>

<style scoped>
/* 初始:整卡沉在画面外(visibility 延时到淡出结束,免得隐去途中还能 Tab 进焦点) */
.login-card {
  width: min(380px, 92vw);
  padding: 36px 32px 30px;
  text-align: center;
  opacity: 0; transform: translateY(52px) scale(0.985); visibility: hidden;
  transition:
    opacity 0.5s ease, transform 0.5s cubic-bezier(0.22, 0.61, 0.36, 1),
    visibility 0s linear 0.5s;
}
.login-card.shown {
  opacity: 1; transform: none; visibility: visible;
  transition: opacity 0.5s ease, transform 0.5s cubic-bezier(0.22, 0.61, 0.36, 1), visibility 0s;
}
.login-logo { width: 64px; height: 64px; border-radius: 50%; object-fit: cover; }
.login-card h1 {
  margin: 10px 0 2px; font-size: 30px; font-weight: 400;
  font-family: var(--font-display); letter-spacing: 0.14em; color: var(--ink);
}
.login-en {
  margin: 0; font-family: var(--font-serif); font-style: italic;
  font-size: 13px; letter-spacing: 0.06em; color: var(--ink-soft);
}
.login-form { display: flex; flex-direction: column; gap: 14px; margin-top: 22px; }
.login-tip { margin-top: 18px; font-size: 12px; color: var(--ink-soft); }

/* 箭头:细一笔、白半透,呼吸式下探;比舞台页的 hint 更小更安静 */
.login-cue {
  position: absolute; left: 50%; bottom: 26px; z-index: 1;
  width: 34px; height: 34px; padding: 0;
  border: none; background: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  opacity: 0.62; transition: opacity 0.45s ease, visibility 0.45s;
  transform: translate(-50%, 0); /* 兜底:reduced-motion 掐掉动画后仍居中 */
  animation: cue-bob 2.6s ease-in-out infinite;
}
.login-cue:hover { opacity: 0.95; }
.login-cue.gone { opacity: 0; visibility: hidden; animation: none; }
.login-cue span {
  display: block; width: 10px; height: 10px;
  border-right: 1.5px solid rgba(255, 255, 255, 0.85);
  border-bottom: 1.5px solid rgba(255, 255, 255, 0.85);
  transform: rotate(45deg);
}
@keyframes cue-bob {
  0%, 100% { transform: translate(-50%, 0); }
  50%      { transform: translate(-50%, 6px); }
}
</style>
