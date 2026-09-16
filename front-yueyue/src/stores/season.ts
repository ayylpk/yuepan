/** 四季皮肤 store(拍板方案):
 *  - localStorage 持久,html[data-season] 切 CSS 变量(style.css 里四套)
 *  - 取图收口在 asset() 一个 resolver:试 `名-季节` → 回落 `-summer` → 回落无后缀,
 *    禁各组件手拼字符串;现在只有夏图,全走"回落无后缀"。
 */
import { defineStore } from 'pinia'

export type Season = 'spring' | 'summer' | 'autumn' | 'winter'

export const SEASONS: { key: Season; label: string; dot: string }[] = [
  { key: 'spring', label: '春', dot: '#6cc298' },
  { key: 'summer', label: '夏', dot: '#3fbce7' },
  { key: 'autumn', label: '秋', dot: '#d08a4e' },
  { key: 'winter', label: '冬', dot: '#86a9d0' },
]

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
      this.apply()
    },
    set(season: Season) {
      this.season = season
      localStorage.setItem(STORAGE_KEY, season)
      this.apply()
    },
    apply() {
      document.documentElement.dataset.season = this.season
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
