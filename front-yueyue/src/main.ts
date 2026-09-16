import { createApp } from 'vue'
import { createPinia } from 'pinia'
import TDesign from 'tdesign-vue-next'
import 'tdesign-vue-next/es/style/index.css' // TDesign 组件样式
import 'highlight.js/styles/stackoverflow-dark.css' // 代码高亮主题(先于站内样式,允许被覆盖)
import './style.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia()) // pinia 必须在 router 前:路由守卫里要用 auth store
app.use(router)
app.use(TDesign)

// v-img-fade:图片加载完再淡入,加载失败也显示(不至于留黑洞)
app.directive('img-fade', {
  mounted: (el: HTMLImageElement) => {
    el.style.opacity = '0'
    el.style.transition = 'opacity 0.6s ease'
    const show = () => (el.style.opacity = '1')
    if (el.complete && el.naturalWidth) show()
    else {
      el.addEventListener('load', show, { once: true })
      el.addEventListener('error', show, { once: true })
    }
  },
})

app.mount('#app')
