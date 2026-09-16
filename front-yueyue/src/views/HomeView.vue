<script setup lang="ts">
// 首页:全幅海岸主图 + 签名元素"粼光"(呼应 banner-home 左侧那片阳光海面),
// 下面是五入口玻璃卡。计数条问后端要,后端没起就整条隐身(不给首页添堵)。
import { onMounted, ref } from 'vue'
import { http } from '@/api/http'
import type { Diary, PageResult } from '@/api/types'
import { asset } from '@/stores/season'

const ENTRIES = [
  { to: '/notes', img: 'banner-notes', zh: '笔记', en: 'NOTES', desc: 'markdown 手记,隐私笔记上锁' },
  { to: '/projects', img: 'banner-projects', zh: '项目', en: 'PROJECTS', desc: '做过什么,一眼数得清' },
  { to: '/videos', img: 'banner-videos', zh: '视频', en: 'VIDEOS', desc: '自留片单,拖动进度条不卡' },
  { to: '/code', img: 'banner-code', zh: '代码', en: 'CODE', desc: '白名单仓库,在线翻源码' },
  { to: '/private', img: 'banner-private', zh: '小屋', en: 'PRIVATE', desc: '第二道锁后面那间洞穴' },
]

const diaryCount = ref<number | null>(null)

onMounted(async () => {
  try {
    // 只问 page 接口拿 count(size=1 少拉数据),日记 = /api/diary(后端三层模板)
    const res = await http.get<PageResult<Diary>>('/api/diary/page?page=1&size=1')
    diaryCount.value = res.count
  } catch { /* 后端没起就安静,hero 有兜底文案 */ }
})
</script>

<template>
  <div>
    <header class="home-hero" :style="{ background: 'linear-gradient(165deg, var(--sky) 8%, var(--sea-mid))' }">
      <img v-img-fade class="hero-img" :src="asset('banner-home')" alt="月畔" />
      <!-- 签名:海面粼光,缓慢漂移;reduced-motion 下由全局规则停掉 -->
      <div class="glitter" aria-hidden="true" />
      <div class="hero-copy">
        <p class="eyebrow">yueyue · a private coast</p>
        <h1>月畔小站</h1>
        <p class="hero-line">
          浪线之外没有人,<span>{{ diaryCount !== null ? `${diaryCount} 篇日记写在架上` : '把这里当海边的一间小屋用' }}</span>
        </p>
      </div>
      <div class="tide-line" aria-hidden="true" />
    </header>

    <section class="site-main entries">
      <router-link v-for="e in ENTRIES" :key="e.to" :to="e.to" class="glass-card entry">
        <img v-img-fade :src="asset(e.img)" :alt="e.zh" loading="lazy" />
        <div class="entry-text">
          <p class="eyebrow">{{ e.en }}</p>
          <h3>{{ e.zh }}</h3>
          <p>{{ e.desc }}</p>
        </div>
      </router-link>
    </section>
  </div>
</template>

<style scoped>
.home-hero {
  position: relative;
  height: min(58vh, 460px);
  overflow: hidden;
  display: flex; align-items: flex-end;
}
.hero-img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }

/* 粼光:两片斜向的暖色径向渐变交叠漂动,压在图的左侧海面上 */
.glitter {
  position: absolute; inset: -20%;
  pointer-events: none;
  background:
    radial-gradient(ellipse 340px 130px at 22% 34%, rgba(255, 252, 235, 0.5), transparent 65%),
    radial-gradient(ellipse 210px 90px at 28% 40%, rgba(255, 244, 200, 0.35), transparent 60%);
  mix-blend-mode: screen;
  animation: drift 14s ease-in-out infinite alternate;
}
@keyframes drift {
  from { transform: translateX(-3.5%) scale(1); opacity: 0.85; }
  to   { transform: translateX(3.5%) scale(1.08); opacity: 1; }
}

.hero-copy {
  position: relative; z-index: 1;
  padding: 0 clamp(20px, 6vw, 72px) 34px;
}
.hero-copy .eyebrow { color: #fff; text-shadow: 0 1px 8px rgba(8, 40, 66, 0.5); }
.hero-copy h1 {
  margin: 4px 0 8px;
  font-size: clamp(34px, 6vw, 58px);
  letter-spacing: 0.18em; color: #fff; font-weight: 700;
  text-shadow: 0 2px 18px rgba(8, 40, 66, 0.5);
}
.hero-line { color: #fff; font-size: 15px; text-shadow: 0 1px 10px rgba(8, 40, 66, 0.55); margin: 0; }

/* 潮线:底缘一道细浪,和下方内容区做软过渡 */
.tide-line {
  position: absolute; left: 0; right: 0; bottom: -1px; height: 26px;
  background: linear-gradient(to top, var(--bg-page), transparent);
}

.entries {
  display: grid; gap: 20px;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}
.entry { display: block; }
.entry img { width: 100%; height: 128px; object-fit: cover; }
.entry-text { padding: 14px 18px 18px; text-align: left; }
.entry-text h3 { margin: 4px 0 6px; font-size: 19px; color: var(--ink); letter-spacing: 0.08em; }
.entry-text p:last-child { margin: 0; font-size: 13px; color: var(--ink-soft); line-height: 1.6; }
.entry .eyebrow { font-size: 10px; }
</style>
