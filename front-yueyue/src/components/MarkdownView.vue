<script setup lang="ts">
// Markdown 渲染:marked 转 HTML → 挂载后对 pre>code 逐个 hljs 高亮。
// 说明:本站是单人私密站,笔记全是你自己写的 markdown,不做 sanitize
// (防的是"别人喂你 XSS",这里那个"别人"不存在);哪天开放访问再补 DOMPurify。
import { nextTick, onMounted, ref, watch } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'

const props = defineProps<{ content: string }>()
const el = ref<HTMLElement>()

marked.setOptions({ gfm: true, breaks: false })

async function render() {
  if (!el.value) return
  el.value.innerHTML = await marked.parse(props.content || '')
  await nextTick()
  el.value.querySelectorAll<HTMLElement>('pre code').forEach((block) => {
    hljs.highlightElement(block)
  })
}

onMounted(render)
watch(() => props.content, render)
</script>

<template>
  <div ref="el" class="md-body" />
</template>
