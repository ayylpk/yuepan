/** 四季皮肤 store(拍板方案):
 *  - localStorage 持久,html[data-season] 切 CSS 变量(style.css 里四套)
 *  - 取图收口在 asset() 一个 resolver:试 `名-季节` → 回落 `-summer` → 回落无后缀,
 *    禁各组件手拼字符串;素材统一命名 `名-季节.jpg`(四季已齐,回落链只是保险丝)。
 */
import { defineStore } from 'pinia'

export type Season = 'spring' | 'summer' | 'autumn' | 'winter'

export const SEASONS: { key: Season; label: string; dot: string }[] = [
  { key: 'spring', label: '春', dot: '#6cc298' },
  { key: 'summer', label: '夏', dot: '#3fbce7' },
  { key: 'autumn', label: '秋', dot: '#d08a4e' },
  { key: 'winter', label: '冬', dot: '#86a9d0' },
]

/** 配图已就位的季节(9/17 拍板:春/冬按钮和整套切换逻辑都保留,图没齐前先不绑定点击,
 *  等季图按"名-季节.jpg"命名丢进 assets 后往数组里加 key 即启用)。
 *  9/19 冬批 10 张落位,启用 winter。
 *  9/26 原图归档出仓:历季原件在 F:/code/backup/yueyue-originals/(spring/ 子目录收春批)。
 *  9/26 春批 10 张落位,启用 spring —— 原件文件夹里 empty/page404 两张名字串了
 *  (page404 文件实为方图嫩叶=empty 位,empty 文件实为 4:3 飘絮公路=404 位),
 *  落位时已按内容纠正文件名,归档件同步纠正;logo 由 1015px PNG 重编码 256² JPG。 */
export const SEASONS_IMAGE_READY: Season[] = ['spring', 'summer', 'autumn', 'winter']
export const hasSeasonImages = (s: Season) => SEASONS_IMAGE_READY.includes(s)

/** 换季溶解时长:html.season-morph 类的存活期(style.css 里有对应过渡规则) */
const MORPH_MS = 650
let morphTimer: number | undefined

// eager 静态收集:构建期就把图打进 bundle,运行期按 key 查表
const ASSETS = import.meta.glob('../assets/*.{jpg,png}', {
  eager: true,
  import: 'default',
}) as Record<string, string>

const STORAGE_KEY = 'yueyue_season'

export const useSeasonStore = defineStore('season', {
  state: () => ({
    season: ((localStorage.getItem(STORAGE_KEY) as Season) || 'summer') as Season,
  }),
  actions: {
    init() {
      // 存档里如果是还没出图的春/冬(早期试验遗留),归位到夏
      if (!hasSeasonImages(this.season)) this.season = 'summer'
      this.apply(false)
    },
    set(season: Season) {
      this.season = season
      localStorage.setItem(STORAGE_KEY, season)
      this.apply(true)
    },
    /** animate=false:首帧直接落位不溶解;true:挂 season-morph 类做 650ms 软着陆 */
    apply(animate = true) {
      const root = document.documentElement
      root.dataset.season = this.season
      if (!animate) return
      root.classList.add('season-morph')
      window.clearTimeout(morphTimer)
      morphTimer = window.setTimeout(() => root.classList.remove('season-morph'), MORPH_MS)
    },
  },
})

/** 全站唯一取图入口。name 不带扩展名,如 'banner-home'。找不到返回 ''(调用方兜底)。 */
export function asset(name: string): string {
  const { season } = useSeasonStore()
  for (const tryName of [`${name}-${season}`, `${name}-summer`, name]) {
    for (const ext of ['jpg', 'png']) {
      const hit = ASSETS[`../assets/${tryName}.${ext}`]
      if (hit) return hit
    }
  }
  console.warn(`[season] 缺图: ${name}(${season})`)
  return ''
}
