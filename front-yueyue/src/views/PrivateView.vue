<script setup lang="ts">
// 隐私小屋(9/17 重塑批4;同日 视频→照片、加资料架):第二道锁。未解锁 = 洞门;解锁后 = 私密日记+照片+资料三格架。
// 版式归一:洞门和墙板统一吃"暗玻璃"配方,不再一半白卡一半暗板。
// 可见性真源在服务端(role=1 未解锁根本不返回 / photo 端点直接 404),这里只做展示与解锁动作。
// 9/26 验收二轮:日记也在屋里就地开卷(原先 router-link 跳 /notes/:id,退出还得自己摸回来);
// "离开小屋=自动落锁"收口在 router 的 afterEach(小屋+带着 ?from=cave 的笔记页算在屋里)。
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { ApiError, http } from '@/api/http'
import type { Diary, FileEntry, PageResult, Photo } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { asset } from '@/stores/season'
import MarkdownView from '@/components/MarkdownView.vue'

const auth = useAuthStore()
const router = useRouter()
const password = ref('')
const busy = ref(false)
const diaries = ref<Diary[]>([])
const photos = ref<Photo[]>([])
const files = ref<FileEntry[]>([])
const tip = ref('')
// lightbox 只吃"图"这一种,照片行和资料图片行走同一个 viewer(源地址不同而已)
const viewer = ref<{ src: string; name: string; sub: string } | null>(null)
// 私密日记就地阅读(9/26):列表接口本来就整行带 content,不用再跳页去拉详情
const reading = ref<Diary | null>(null)
function editReading() {
  if (!reading.value) return
  // from=cave = 告诉 router"这是小屋的延伸页",别触发自动落锁;edit=1 进页即编辑态
  router.push(`/notes/${reading.value.id}?from=cave&edit=1`)
}

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
  // 9/26 验收修:日记架原来是 9/16 前的旧口径"拉全量前端筛"——请求既没 role=1
  // 也没真生效过(size 参数名对不上后端的 page_size),后端默认 role=0 只发公开条目,
  // 再被 filter(d.role===1) 滤成恒空。改成和照片/资料架同款:服务端筛 role=1。
  // 前端 filter 留着当第二道保险(会话失步时也不把公开条目摆上屋架)。
  diaries.value = []
  photos.value = []
  files.value = []
  try {
    const page = await http.get<PageResult<Diary>>('/api/diary/page?page=1&page_size=100&role=1')
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
  if (e.key === 'Escape') {
    viewer.value = null
    reading.value = null
  }
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
        <button v-for="d in diaries" :key="d.id" type="button" class="row row-diary" @click="reading = d">
          <strong>{{ d.title }}</strong><em>{{ d.created_at.slice(0, 16) }} · 就地看</em>
        </button>
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

    <!-- 私密日记就地开卷:读完合上还在小屋;编辑才出门,带 from=cave 户籍免被落锁 -->
    <div v-if="reading" class="cave-lightbox" @click="reading = null">
      <article class="cave-note" @click.stop>
        <header class="note-head">
          <h3>{{ reading.title }}</h3>
          <em>{{ reading.created_at.slice(0, 16) }} · 写于小屋</em>
        </header>
        <div class="note-body">
          <MarkdownView :content="reading.content" />
        </div>
        <footer class="note-foot">
          <t-button variant="outline" theme="default" size="small" @click="reading = null">合上继续待小屋</t-button>
          <t-button theme="primary" size="small" @click="editReading">去编辑</t-button>
        </footer>
      </article>
    </div>
  </div>
</template>

<style scoped>
/* 洞穴底色:10/09 起随季(--cave-* 令牌见 style.css 四季块)。
   原来是写死的 #0b2733 + #77fbfc,成了全站唯一不随季的页面,进出小屋会整屏跳变。 */
.cave { background-color: var(--cave-bg); }
.cave-bg { object-position: center; }

/* ---- 暗玻璃配方:洞门与墙板同源,强调光跟季走但保持"洞里"的暗调 ---- */
.gate, .room {
  backdrop-filter: blur(14px);
  border: 1px solid var(--cave-line);
  color: var(--cave-text);
}
.gate {
  width: min(360px, 92vw); padding: 36px 30px 30px; text-align: center;
  background: var(--cave-glass);
  border-radius: 18px;
  box-shadow: 0 24px 60px -24px rgba(0, 0, 0, 0.65);
  animation: copy-rise 0.8s 0.3s cubic-bezier(0.22, 0.61, 0.36, 1) backwards;
}
.gate h1 {
  margin: 0; font-size: 32px; font-weight: 400;
  font-family: var(--font-display); letter-spacing: 0.24em; text-indent: 0.24em; color: #fff;
  text-shadow: 0 0 22px color-mix(in srgb, var(--private-glow) 38%, transparent);
}
.gate-en {
  margin: 4px 0 14px; font-family: var(--font-serif); font-style: italic;
  font-size: 13px; letter-spacing: 0.06em;
  color: color-mix(in srgb, var(--private-glow) 82%, transparent);
}
.gate-desc { font-size: 13.5px; color: var(--cave-text-soft); margin: 0 0 18px; }
.gate :deep(.t-input__wrap) { margin-bottom: 14px; }

.room {
  width: min(760px, 94vw);
  background: var(--cave-glass);
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
  letter-spacing: 0.05em; color: var(--cave-text-soft);
}
.tip { color: var(--private-warm); font-size: 13px; margin-top: 12px; }
.shelf { margin-top: 28px; }
.shelf h2 {
  font-size: 15px; letter-spacing: 0.12em; color: var(--private-glow);
  border-bottom: 1px solid var(--cave-line); padding-bottom: 8px;
  display: flex; align-items: baseline; gap: 8px;
}
.shelf h2 span { font-size: 12px; color: var(--cave-text-soft); }
.row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 16px; margin-top: 10px; border-radius: 12px;
  background: var(--cave-row); border: 1px solid var(--cave-line);
  transition: background-color 0.22s ease, border-color 0.22s ease;
}
.row:hover {
  background: var(--cave-row-hover);
  border-color: color-mix(in srgb, var(--private-glow) 34%, transparent);
}
.row strong { color: var(--cave-text); font-weight: 500; }
.row em { font-style: normal; font-size: 12px; color: var(--cave-text-soft); }
/* 照片/资料行:缩略图(或类型徽章)+ 两行字,点开大图/触发下载 */
.row-photo {
  width: 100%; font: inherit; text-align: left; cursor: pointer;
  gap: 12px; align-items: center;
}
/* 日记架行现在是 button(就地点开),把浏览器默认皮肤褪掉,继承 .row 的玻璃配方 */
.row-diary {
  width: 100%; font: inherit; text-align: left; cursor: pointer;
  color: inherit;
}
.row-diary strong { font-weight: 500; }
/* 就地开卷的纸面板:日记正文按站内亮色口径排版,垫在暗玻璃幕布上 */
.cave-note {
  width: min(720px, 92vw); max-height: 86vh; overflow: auto;
  background: var(--card); color: var(--ink); border-radius: 16px;
  padding: 24px clamp(18px, 4vw, 34px) 20px;
  box-shadow: 0 24px 60px -24px rgba(0, 0, 0, 0.7);
  cursor: auto;
}
.note-head { border-bottom: 1px solid var(--line); padding-bottom: 12px; margin-bottom: 14px; }
.note-head h3 { margin: 0; font-family: var(--font-display); font-size: 22px; font-weight: 600; }
.note-head em { font-style: normal; font-size: 12px; color: var(--ink-soft); }
.note-body { font-size: 15px; }
.note-foot { display: flex; justify-content: flex-end; gap: 8px; margin-top: 18px; padding-top: 12px; border-top: 1px solid var(--line); }
.row-photo img { width: 46px; height: 46px; object-fit: cover; border-radius: 8px; flex-shrink: 0; }
/* 资料行没缩略图,用暗色徽章占同一格位 */
.rf-ext {
  flex: none; width: 46px; text-align: center; text-transform: uppercase;
  font-family: var(--font-mono); font-size: 10.5px; letter-spacing: 0.03em;
  padding: 6px 4px; border-radius: 8px;
  background: color-mix(in srgb, var(--private-glow) 10%, transparent);
  border: 1px solid var(--cave-line);
  color: var(--private-glow);
}
.row-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.row-text strong, .row-text em { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.none { color: var(--cave-text-soft); font-size: 13px; }

.cave-lightbox {
  position: fixed; inset: 0; z-index: 300;
  background: color-mix(in srgb, var(--cave-bg) 92%, #000);
  backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  cursor: zoom-out;
}
.cave-lightbox figure { margin: 0; text-align: center; }
.cave-lightbox img { max-width: 88vw; max-height: 82vh; border-radius: 10px; }
.cave-lightbox figcaption { margin-top: 12px; font-size: 13px; color: var(--cave-text); }
</style>
