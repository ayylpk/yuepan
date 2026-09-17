<script setup lang="ts">
// 隐私小屋(9/17 重塑批4;同日 视频→照片、加资料架):第二道锁。未解锁 = 洞门;解锁后 = 私密日记+照片+资料三格架。
// 版式归一:洞门和墙板统一吃"暗玻璃"配方,不再一半白卡一半暗板。
// 可见性真源在服务端(role=1 未解锁根本不返回 / photo 端点直接 404),这里只做展示与解锁动作。
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http } from '@/api/http'
import type { Diary, FileEntry, PageResult, Photo } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { asset } from '@/stores/season'

const auth = useAuthStore()
const password = ref('')
const busy = ref(false)
const diaries = ref<Diary[]>([])
const photos = ref<Photo[]>([])
const files = ref<FileEntry[]>([])
const tip = ref('')
// lightbox 只吃"图"这一种,照片行和资料图片行走同一个 viewer(源地址不同而已)
const viewer = ref<{ src: string; name: string; sub: string } | null>(null)

const FILE_IMG_EXT = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'])
const fmtSize = (n: number) => (n > 1 << 20 ? (n / (1 << 20)).toFixed(1) + ' MB' : Math.round(n / 1024) + ' KB')

function photoView(p: Photo) {
  viewer.value = { src: `/api/photo/${p.id}/file`, name: p.name, sub: `${p.created_at.slice(0, 16)} · ${fmtSize(p.size)}` }
}
function openCaveFile(f: FileEntry) {
  // 图片走灯箱;其余格式洞里也只做"落盘下载"(完整预览器在资料页,那边是公开区)
  if (FILE_IMG_EXT.has((f.type || '').toLowerCase())) {
    viewer.value = { src: `/api/file/${f.id}/raw`, name: f.name, sub: `${f.created_at.slice(0, 16)} · ${fmtSize(f.size)}` }
  } else {
    location.assign(`/api/file/${f.id}/download`)
  }
}

async function loadPrivate() {
  // 日记:全量拉回来按 role 筛(未解锁时后端不发隐私条目,筛了也白筛,天然安全)
  // 照片:photo 端点吃 page_size 参数,解锁态下 role=1 直接让服务端筛(比拉全量再滤省)
  diaries.value = []
  photos.value = []
  files.value = []
  try {
    const page = await http.get<PageResult<Diary>>('/api/diary/page?page=1&size=100')
    diaries.value = page.data.filter((d) => d.role === 1)
  } catch { /* 日记接口挂了不拦后面的区 */ }
  try {
    const res = await http.get<PageResult<Photo>>('/api/photo/page?page=1&page_size=100&role=1')
    photos.value = res.data
  } catch { /* 未解锁/接口异常时静默:服务端本来也不该发 */ }
  try {
    const res = await http.get<PageResult<FileEntry>>('/api/file/page?page=1&page_size=100&role=1')
    files.value = res.data
  } catch { /* 同上 */ }
  if (auth.private && !diaries.value.length && !photos.value.length && !files.value.length) {
    tip.value = '屋里还空。若你确定存过 role=1 的日记/照片/资料,检查一下后端 session 是否认了这把锁'
  }
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') viewer.value = null
}
onMounted(() => {
  if (auth.private) loadPrivate()
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

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
  viewer.value = null
  MessagePlugin.info('已重新上锁')
}
</script>

<template>
  <div class="full-stage cave">
    <img v-img-fade class="full-stage__bg cave-bg" :src="asset('banner-private')" alt="" />
    <div class="full-stage__scrim" aria-hidden="true" />

    <!-- 未解锁:洞门 -->
    <div v-if="!auth.private" class="gate">
      <h1>小屋</h1>
      <p class="gate-en">the cave · second lock</p>
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
          <h1>小屋<span class="room-on">灯亮着</span></h1>
          <p class="room-en">the cave · unlocked</p>
        </div>
        <div class="room-actions">
          <t-button variant="outline" theme="warning" @click="lock">重新上锁</t-button>
        </div>
      </div>
      <p v-if="tip" class="tip">{{ tip }}</p>

      <section class="shelf">
        <h2>私密日记<span>{{ diaries.length }}</span></h2>
        <router-link v-for="d in diaries" :key="d.id" :to="`/notes/${d.id}`" class="row">
          <strong>{{ d.title }}</strong><em>{{ d.created_at.slice(0, 16) }}</em>
        </router-link>
        <p v-if="!diaries.length && !tip" class="none">还没有收进来的日记</p>
      </section>

      <section class="shelf">
        <h2>私密照片<span>{{ photos.length }}</span></h2>
        <button v-for="p in photos" :key="p.id" type="button" class="row row-photo" @click="photoView(p)">
          <img :src="`/api/photo/${p.id}/file`" :alt="p.name" loading="lazy" />
          <span class="row-text"><strong>{{ p.name }}</strong><em>{{ p.created_at.slice(0, 16) }} · {{ (p.size / 1024 / 1024).toFixed(1) }} MB</em></span>
        </button>
        <p v-if="!photos.length" class="none">还没有收进来的照片</p>
      </section>

      <section class="shelf">
        <h2>私密资料<span>{{ files.length }}</span></h2>
        <button v-for="f in files" :key="f.id" type="button" class="row row-photo" @click="openCaveFile(f)">
          <span class="rf-ext">{{ f.type || 'file' }}</span>
          <span class="row-text"><strong>{{ f.name }}</strong><em>{{ f.created_at.slice(0, 16) }} · {{ fmtSize(f.size) }} · {{ FILE_IMG_EXT.has((f.type || '').toLowerCase()) ? '点开看' : '下载看' }}</em></span>
        </button>
        <p v-if="!files.length" class="none">还没有收进来的资料</p>
      </section>
    </div>

    <!-- 屋内大图预览(私密照片 + 图片类资料共用):Esc/点背景关 -->
    <div v-if="viewer" class="cave-lightbox" @click="viewer = null">
      <figure @click.stop>
        <img :src="viewer.src" :alt="viewer.name" />
        <figcaption>{{ viewer.name }} · {{ viewer.sub }}</figcaption>
      </figure>
    </div>
  </div>
</template>

<style scoped>
/* 洞穴图本身就暗,骨架的兜底色换成洞穴蓝黑;压顶渐变对暗图够用,不再叠 */
.cave { background-color: #0b2733; }
.cave-bg { object-position: center; }

/* ---- 暗玻璃配方:洞门与墙板同源,场景专属色(--private-glow/warm)不随季 ---- */
.gate, .room {
  backdrop-filter: blur(14px);
  border: 1px solid rgba(119, 251, 252, 0.18);
  color: #dfeef7;
}
.gate {
  width: min(360px, 92vw); padding: 36px 30px 30px; text-align: center;
  background: rgba(8, 30, 40, 0.72);
  border-radius: 18px;
  box-shadow: 0 24px 60px -24px rgba(0, 0, 0, 0.65);
  animation: copy-rise 0.8s 0.3s cubic-bezier(0.22, 0.61, 0.36, 1) backwards;
}
.gate h1 {
  margin: 0; font-size: 32px; font-weight: 400;
  font-family: var(--font-display); letter-spacing: 0.24em; text-indent: 0.24em; color: #fff;
  text-shadow: 0 0 22px rgba(119, 251, 252, 0.35);
}
.gate-en {
  margin: 4px 0 14px; font-family: var(--font-serif); font-style: italic;
  font-size: 13px; letter-spacing: 0.06em; color: rgba(119, 251, 252, 0.8);
}
.gate-desc { font-size: 13.5px; color: rgba(223, 238, 247, 0.75); margin: 0 0 18px; }
.gate :deep(.t-input__wrap) { margin-bottom: 14px; }

.room {
  width: min(760px, 94vw);
  background: rgba(9, 32, 42, 0.78);
  border-radius: 20px; padding: 30px clamp(16px, 4vw, 36px) 34px;
  animation: copy-rise 0.8s 0.25s cubic-bezier(0.22, 0.61, 0.36, 1) backwards;
}
.room-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; flex-wrap: wrap; }
.room-head h1 {
  margin: 0; font-size: 30px; font-weight: 400;
  font-family: var(--font-display); letter-spacing: 0.18em; color: #fff;
  display: flex; align-items: baseline; gap: 10px;
}
.room-on {
  font-family: var(--font-sans); font-size: 12px; letter-spacing: 0.08em;
  color: var(--private-glow);
}
.room-head h1 + .room-en { margin: 2px 0 0; }
.room-en {
  font-family: var(--font-serif); font-style: italic; font-size: 12.5px;
  letter-spacing: 0.05em; color: rgba(223, 238, 247, 0.6);
}
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
  background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(119, 251, 252, 0.15);
  transition: background-color 0.22s ease, border-color 0.22s ease;
}
.row:hover { background: rgba(255, 255, 255, 0.1); border-color: rgba(119, 251, 252, 0.32); }
.row strong { color: #eef8fd; font-weight: 500; }
.row em { font-style: normal; font-size: 12px; color: rgba(223, 238, 247, 0.6); }
/* 照片/资料行:缩略图(或类型徽章)+ 两行字,点开大图/触发下载 */
.row-photo {
  width: 100%; font: inherit; text-align: left; cursor: pointer;
  gap: 12px; align-items: center;
}
.row-photo img { width: 46px; height: 46px; object-fit: cover; border-radius: 8px; flex-shrink: 0; }
/* 资料行没缩略图,用暗色徽章占同一格位 */
.rf-ext {
  flex: none; width: 46px; text-align: center; text-transform: uppercase;
  font-family: var(--font-mono); font-size: 10.5px; letter-spacing: 0.03em;
  padding: 6px 4px; border-radius: 8px;
  background: rgba(119, 251, 252, 0.1); border: 1px solid rgba(119, 251, 252, 0.25);
  color: var(--private-glow);
}
.row-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.row-text strong, .row-text em { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.none { color: rgba(223, 238, 247, 0.5); font-size: 13px; }

.cave-lightbox {
  position: fixed; inset: 0; z-index: 300;
  background: rgba(4, 16, 24, 0.9);
  backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  cursor: zoom-out;
}
.cave-lightbox figure { margin: 0; text-align: center; }
.cave-lightbox img { max-width: 88vw; max-height: 82vh; border-radius: 10px; }
.cave-lightbox figcaption { margin-top: 12px; font-size: 13px; color: rgba(223, 238, 247, 0.85); }
</style>
