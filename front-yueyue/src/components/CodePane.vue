<script setup lang="ts">
// VSCode 式代码面板:hljs 高亮。9/17 从 CodeView 的 paintCode 抽出来成公共件
// —— 代码页和资料页的文本预览吃同一块屏。
// 9/26 验收:行号栏scoped 样式从没命中过动态节点(挤成横排"1 2 3…"),
// 用户拍板直接撤掉,顺手把"切换文件不刷新"(appendChild 不清旧节点)修了。
// 高亮走 textContent + hljs,不拼 innerHTML(避免注入面);主题=全局 vs2015。
import { nextTick, ref, watch } from 'vue'
import hljs from 'highlight.js'

const props = defineProps<{ content: string; lang?: string }>()
const box = ref<HTMLElement | null>(null)

function paint() {
  const el = box.value
  if (!el) return
  // 编辑器对齐口径:结尾那个换行符不另起"空行"(a\nb\n = 2 行,不是 3 行)
  const body = props.content.replace(/\n$/, '')
  const pre = document.createElement('pre')
  if (props.lang) {
    const code = document.createElement('code')
    code.className = `language-${props.lang}`
    code.textContent = body
    pre.appendChild(code)
    el.replaceChildren(pre) // 原子换整块;原 appendChild 不清旧的=切文件看着"不刷新"
    hljs.highlightElement(code)
  } else {
    pre.textContent = body // 认不出的语言纯文本兜底
    el.replaceChildren(pre)
  }
}

// content/lang 变化重画;immediate 首帧在 mount 后的 nextTick 里落画
watch(() => [props.content, props.lang] as const, () => nextTick(paint), { immediate: true })
</script>

<template>
  <div ref="box" class="code-pane" />
</template>

<style scoped>
.code-pane { font-family: var(--font-mono); font-size: 14px; line-height: 21px; color: #d4d4d4; } /* 14/21 = VSCode 默认字号行高 */
/* 行号栏(9/26 撤):左边 4px 本来是给 sticky 数字栏留位的,撤栏后补回 18px 对称 */
.code-pane :deep(pre) { margin: 0; padding: 14px 18px; overflow: visible; }
/* vs2015 主题给 .hljs 自带 padding/滚动/底色,壳式排版里全要卸掉(颜色留着) */
.code-pane :deep(pre code) { display: block; background: none; padding: 0; overflow: visible; }
</style>
