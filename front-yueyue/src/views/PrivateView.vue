<script setup lang="ts">
// 隐私小屋:第二道锁。未解锁 = 一扇发着霓虹光的洞门;解锁后 = 私密日记+私密视频架。
// 可见性真源在服务端(role=1 未解锁根本不返回),这里只做展示与解锁动作。
import { onMounted, ref } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http } from '@/api/http'
import type { Diary, PageResult, VideoEntry } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { asset } from '@/stores/season'

const auth = useAuthStore()
const password = ref('')
const busy = ref(false)
const diaries = ref<Diary[]>([])
const videos = ref<VideoEntry[]>([])
const tip = ref('')

async function loadPrivate() {
  // 全量拉回来再按 role 筛:未解锁时后端根本不发隐私条目,筛了也白筛,天然安全
  diaries.value = []
  videos.value = []
  try {
    const page = await http.get<PageResult<Diary>>('/api/diary/page?page=1&size=100')
    diaries.value = page.data.filter((d) => d.role === 1)
  } catch { /* 日记接口挂了不拦视频区 */ }
  try {
    videos.value = ((await http.get<VideoEntry[]>('/api/videos')) || []).filter((v) => v.role === 1)
  } catch { /* /api/videos 未实现,静默 */ }
  if (auth.private && !diaries.value.length && !videos.value.length) {
    tip.value = '屋里还空。若你确定写过 role=1 的日记 —— 后端 session 还没接,隐私条目暂时不会下发(见 back-yueyue README TODO 2)'
  }
}

async function unlock() {
  if (!password.value) return
  busy.value = true
  try {
    await auth.unlock(password.value)
    MessagePlugin.success('门开了')
    password.value = ''
    await loadPrivate()
  } catch (e) {
    MessagePlugin.error(e instanceof ApiError ? e.message : '解锁失败')
  } finally {
    busy.value = false
  }
}

async function lock() {
  await auth.lock()
  tip.value = ''
  MessagePlugin.info('已重新上锁')
}

onMounted(() => { if (auth.private) loadPrivate() })
</script>

<template>
  <div class="cave" :style="{ backgroundImage: `url(${asset('banner-private')})` }">
    <!-- 未解锁:洞门 -->
    <div v-if="!auth.private" class="gate glass-card">
      <h1>小屋</h1>
      <p class="eyebrow">private · second lock</p>
      <p class="gate-desc">这里面的东西,不解锁就连"存在"都不知道存在。</p>
      <t-input
        v-model="password" type="password" size="large" placeholder="解锁密码"
        :autofocus="true" @enter="unlock"
      />
      <t-button theme="primary" size="large" block :loading="busy" @click="unlock">开灯进屋</t-button>
    </div>

    <!-- 已解锁:屋内 -->
    <div v-else class="room">
      <div class="room-head">
        <div>
          <p class="eyebrow" style="color: var(--private-glow)">PRIVATE ROOM · 灯亮着</p>
          <h1>小屋</h1>
        </div>
        <div class="room-actions">
          <t-button variant="outline" theme="warning" @click="lock">重新上锁</t-button>
        </div>
      </div>
      <p v-if="tip" class="tip">{{ tip }}</p>

      <section class="shelf">
        <h2>私密日记<span>{{ diaries.length }}</span></h2>
        <router-link v-for="d in diaries" :key="d.id" :to="`/notes/${d.id}`" class="row glass-card">
          <strong>{{ d.title }}</strong><em>{{ d.created_at.slice(0, 16) }}</em>
        </router-link>
        <p v-if="!diaries.length && !tip" class="none">还没有收进来的日记</p>
      </section>

      <section class="shelf">
        <h2>私密视频<span>{{ videos.length }}</span></h2>
        <div v-for="v in videos" :key="v.id" class="row glass-card">
          <strong>{{ v.title }}</strong><em>{{ v.created_at.slice(0, 10) }}</em>
        </div>
        <p v-if="!videos.length" class="none">还没有收进来的视频</p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.cave {
  min-height: calc(100vh - 64px);
  background-size: cover; background-position: center;
  background-color: #0b2733; /* 图加载前的洞穴底色 */
  display: flex; align-items: center; justify-content: center;
  padding: 40px 16px;
}
.gate { width: min(360px, 92vw); padding: 34px 30px; text-align: center; }
.gate h1 { margin: 0; font-size: 30px; letter-spacing: 0.2em; color: var(--ink); }
.gate .eyebrow { margin: 4px 0 14px; }
.gate-desc { font-size: 13.5px; color: var(--ink-soft); margin: 0 0 18px; }
.gate :deep(.t-input__wrap) { margin-bottom: 14px; }

.room {
  width: min(760px, 94vw);
  background: rgba(11, 39, 51, 0.78); /* 洞穴里的半透明墙板 */
  backdrop-filter: blur(8px);
  border-radius: 20px; padding: 30px clamp(16px, 4vw, 36px);
  color: #dfeef7;
}
.room-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; flex-wrap: wrap; }
.room-head h1 { margin: 2px 0 0; font-size: 28px; letter-spacing: 0.18em; color: #fff; }
.tip { color: var(--private-warm); font-size: 13px; margin-top: 12px; }
.shelf { margin-top: 28px; }
.shelf h2 {
  font-size: 15px; letter-spacing: 0.12em; color: var(--private-glow);
  border-bottom: 1px solid rgba(119, 251, 252, 0.25); padding-bottom: 8px;
  display: flex; align-items: baseline; gap: 8px;
}
.shelf h2 span { font-size: 12px; color: rgba(223, 238, 247, 0.55); }
.row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 16px; margin-top: 10px; border-radius: 12px;
  background: rgba(255, 255, 255, 0.06); border-color: rgba(119, 251, 252, 0.15);
  box-shadow: none;
}
.row strong { color: #eef8fd; font-weight: 500; }
.row em { font-style: normal; font-size: 12px; color: rgba(223, 238, 247, 0.6); }
.none { color: rgba(223, 238, 247, 0.5); font-size: 13px; }
</style>
