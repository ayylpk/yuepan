<script setup lang="ts">
// 首页(9/17 重塑批3):全屏季节舞台 + 压缝"船坞卡"五入口。
// 签名动效两件套:海面粼光(锚位随季迁移——夏在左侧阳光海面,秋在右侧落日光晕)、
// 船坞卡错峰上浮。计数条问后端要,后端没起就一句话兜底(不给首页添堵)。
import { onMounted, ref } from 'vue'
import { http } from '@/api/http'
import type { Diary, PageResult } from '@/api/types'
import { asset } from '@/stores/season'
import StageHero from '@/components/StageHero.vue'

const ENTRIES = [
  { to: '/notes', img: 'banner-notes', zh: '笔记', en: 'notes', desc: 'markdown 手记,隐私笔记上锁' },
  { to: '/projects', img: 'banner-projects', zh: '项目', en: 'projects', desc: '做过什么,一眼数得清' },
  { to: '/photos', img: 'banner-photos', zh: '照片', en: 'photos', desc: '挑出来的钉成一面墙' },
  // 资料卡暂时借首页那张海景(banner-files 出图后换成自己名字即可)
  { to: '/files', img: 'banner-home', zh: '资料', en: 'files', desc: 'txt/pdf 点开即看的架' },
  { to: '/code', img: 'banner-code', zh: '代码', en: 'code', desc: '白名单仓库,在线翻源码' },
  { to: '/private', img: 'banner-private', zh: '小屋', en: 'the cave', desc: '第二道锁后面那间洞穴' },
]

const diaryCount = ref<number | null>(null)

onMounted(async () => {
  try {
    // 只问 page 接口拿 count(page_size=1 少拉数据;9/26 修:原来写 size= 后端不认,一直白拉 10 条)
    const res = await http.get<PageResult<Diary>>('/api/diary/page?page=1&page_size=1')
    diaryCount.value = res.count
  } catch { /* 后端没起就安静,hero 有兜底文案 */ }
})
</script>

<template>
  <div class="home">
    <div class="home-stage-wrap">
      <StageHero
        :img="asset('banner-home')" title="月畔"
        en="yueyue · a private coast" :hint="false"
      >
        <p class="home-line">
          浪线之外没有人,<span>{{ diaryCount !== null ? `${diaryCount} 篇日记写在架上` : '把这里当海边的一间小屋用' }}</span>
        </p>
      </StageHero>
      <!-- 签名:海面粼光缓慢漂动;锚位见 CSS(夏左秋右),reduced-motion 由全局规则停掉 -->
      <div class="glitter" aria-hidden="true" />
    </div>

    <!-- 船坞卡:骑在舞台与页面底色的交界线上,像五扇开向海的窗 -->
    <nav class="dock stagger" aria-label="站点栏目">
      <router-link
        v-for="(e, i) in ENTRIES" :key="e.to" :to="e.to"
        class="dock-card card" :style="{ '--i': i }"
      >
        <img v-img-fade :src="asset(e.img)" :alt="e.zh" loading="lazy" />
        <div class="dock-text">
          <h3>{{ e.zh }}<em>{{ e.en }}</em></h3>
          <p>{{ e.desc }}</p>
        </div>
      </router-link>
    </nav>
  </div>
</template>

<style scoped>
.home-stage-wrap { position: relative; }

/* 粼光:两片斜向暖色径向渐变交叠漂动(mix-blend screen 只提亮不遮图) */
.glitter {
  position: absolute; inset: 0; z-index: 2;
  pointer-events: none;
  --gl-x: 22%; --gl-y: 34%; /* 夏:banner-home 左侧阳光海面 */
  background:
    radial-gradient(ellipse 340px 130px at var(--gl-x) var(--gl-y), rgba(255, 252, 235, 0.5), transparent 65%),
    radial-gradient(ellipse 210px 90px at calc(var(--gl-x) + 6%) calc(var(--gl-y) + 6%), rgba(255, 244, 200, 0.35), transparent 60%);
  mix-blend-mode: screen;
  animation: drift 14s ease-in-out infinite alternate;
}
html[data-season='autumn'] .glitter { --gl-x: 82%; --gl-y: 24%; } /* 秋:落日光晕在右上 */

/* slot 进去的那句动态文案:跟主标动线同拍 */
.home-line {
  margin: 12px 0 0; font-size: 15px; color: rgba(255, 255, 255, 0.92);
  text-shadow: 0 1px 10px rgba(8, 40, 66, 0.55);
  animation: copy-rise 0.8s 0.58s cubic-bezier(0.22, 0.61, 0.36, 1) backwards;
}

/* ---- 船坞卡 ---- */
.dock {
  position: relative; z-index: 3;
  margin-top: clamp(-92px, -8.5vh, -60px);
  padding: 0 clamp(16px, 4vw, 32px) clamp(56px, 9vh, 96px);
  max-width: 1180px; margin-left: auto; margin-right: auto;
  /* 9/17 起六扇窗:auto-fit 让 5/6 列随宽度自己换,不用手改断点 */
  display: grid; grid-template-columns: repeat(auto-fit, minmax(176px, 1fr)); gap: 14px;
}
/* --rise-base:错峰起点等舞台标题动线走完 */
.dock { --rise-base: 650ms; }
.dock-card {
  display: block; cursor: pointer;
  transition: transform 0.28s ease, box-shadow 0.28s ease, border-color 0.28s ease;
}
.dock-card:hover {
  transform: translateY(-5px);
  border-color: color-mix(in srgb, var(--sea-mid) 55%, var(--line));
  box-shadow: 0 20px 40px -18px rgba(20, 90, 140, 0.45);
}
.dock-card img { width: 100%; height: 92px; object-fit: cover; transition: transform 0.4s ease; }
.dock-card:hover img { transform: scale(1.06); }
.dock-card { overflow: hidden; } /* 让 img scale 被圆角裁住 */
.dock-text { padding: 12px 14px 15px; }
.dock-text h3 {
  margin: 0; font-size: 18px; font-weight: 400;
  font-family: var(--font-display); letter-spacing: 0.1em; color: var(--ink);
  display: flex; align-items: baseline; gap: 8px;
}
.dock-text h3 em {
  font-style: italic; font-family: var(--font-serif);
  font-size: 11px; letter-spacing: 0.04em; color: var(--ink-soft);
}
.dock-text p { margin: 5px 0 0; font-size: 12px; color: var(--ink-soft); line-height: 1.55; }

@media (max-width: 1000px) {
  .dock { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 640px) {
  /* 窄屏:五扇窗改成横向船坞,左右拖动 */
  .dock {
    display: flex; overflow-x: auto; gap: 12px;
    scroll-snap-type: x mandatory;
    padding-bottom: 64px;
  }
  .dock-card { flex: 0 0 216px; scroll-snap-align: start; }
}
</style>
