import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    // '@' 指向 src,导入不用再数 ../../
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    proxy: {
      // 开发期同源转发:前端所有 /api 请求 → FastAPI(8000),省掉跨域
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
