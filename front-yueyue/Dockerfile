# 月畔小站 前端镜像:node 构建 → nginx 托管 dist(两阶段构建)
#
# 为什么前端容器里还带一个 nginx:前端要的不仅是静态文件,还需要
#   - SPA fallback(路由是 createWebHistory,刷新 /notes/12 不能 404)
#   - /api 反代到后端容器(同源 → 前端代码零改动、无跨域、Cookie 自动带)
FROM node:22-alpine AS build
WORKDIR /src
# 先只拷依赖清单,依赖层能缓存
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# build = vue-tsc -b && vite build;类型错误会让镜像构建直接失败(相当于一道闸门)
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
