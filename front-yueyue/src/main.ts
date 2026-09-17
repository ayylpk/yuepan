import { createApp } from 'vue'
import { createPinia } from 'pinia'
import TDesign from 'tdesign-vue-next'
import 'tdesign-vue-next/es/style/index.css' // TDesign 组件样式
import 'highlight.js/styles/vs2015.css' // 代码高亮主题=VSCode 同款色卡(先于站内样式,允许被覆盖)
import './style.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia()) // pinia 必须在 router 前:路由守卫里要用 auth store
app.use(router)
app.use(TDesign)

// v-img-fade:图片加载完再淡入,加载失败也显示(不至于留黑洞)。
// 9/17 重塑:补 updated 钩子——换季时 :src 会变,旧版只处理 mounted,
// 新图是"硬切进来的",这里先压黑→预加载→到位再淡入,卡片图也吃换季溶解。
app.directive('img-fade', {
  mounted: (el: HTMLImageElement) => {
    el.style.transition = 'opacity 0.6s ease'
    el.style.opacity = '0'
    el.dataset.fadeSrc = el.src // 记录初值给 updated 比对
    const show = () => (el.style.opacity = '1')
    if (el.complete && el.naturalWidth) show()
    else {
      el.addEventListener('load', show, { once: true })
      el.addEventListener('error', show, { once: true })
    }
  },
  updated: (el: HTMLImageElement, binding) => {
    const next = String(binding.value ?? '')
    if (!next || next === el.dataset.fadeSrc) return
    el.dataset.fadeSrc = next
    el.style.opacity = '0'
    if (next === el.src) {
      // Vue 已把 src 换上(元素自己会 load),等它的事件淡入;失败路径也显示
      el.addEventListener('load', () => (el.style.opacity = '1'), { once: true })
      el.addEventListener('error', () => (el.style.opacity = '1'), { once: true })
      return
    }
    const pre = new Image()
    pre.onload = () => { el.src = next; el.style.opacity = '1' }
    pre.onerror = () => { el.src = next; el.style.opacity = '1' } // 露碎图图标好过黑洞
    pre.src = next
  },
})

app.mount('#app')
