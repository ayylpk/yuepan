<script setup lang="ts">
// VSCode 式代码面板:行号栏(sticky 左缘)+ hljs 高亮。9/17 从 CodeView 的
// paintCode 抽出来成公共件 —— 代码页和资料页的文本预览吃同一块屏。
// 高亮走 textContent + hljs,不拼 innerHTML(避免注入面);主题=全局 vs2015。
import { nextTick, ref, watch } from 'vue'
import hljs from 'highlight.js'

const props = defineProps<{ content: string; lang?: string }>()
const box = ref<HTMLElement | null>(null)

function paint() {
  const el = box.value
  if (!el) return
  // 行号与编辑器对齐的口径:结尾那个换行符不另起"空行"(a\nb\n = 2 行,不是 3 行)
  const body = props.content.replace(/\n$/, '')
  const lineCount = body.split('\n').length
  const wrap = document.createElement('div')
  wrap.className = 'vs'
  const nums = document.createElement('div')
  nums.className = 'ln'
  nums.textContent = Array.from({ length: lineCount }, (_, i) => i + 1).join('\n')
  const pre = document.createElement('pre')
  if (props.lang) {
    const code = document.createElement('code')
    code.className = `language-${props.lang}`
    code.textContent = body
    pre.appendChild(code)
    wrap.append(nums, pre)
    el.appendChild(wrap)
    hljs.highlightElement(code)
  } else {
    pre.textContent = body // 认不出的语言纯文本兜底
    wrap.append(nums, pre)
    el.appendChild(wrap)
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
.vs { display: flex; align-items: flex-start; }
/* 行号栏 sticky 左缘:代码横滚时它不动,底色盖住从下面滑过的字符(外层需自备 #1e1e1e 底) */
.ln {
  position: sticky; left: 0; z-index: 1; flex: none;
  padding: 14px 16px 14px 14px; text-align: right; white-space: pre;
  user-select: none; color: #858585; background: #1e1e1e;
}
.code-pane :deep(pre) { flex: 1 1 auto; margin: 0; padding: 14px 18px 14px 4px; overflow: visible; }
/* vs2015 主题给 .hljs 自带 padding/滚动/底色,壳式排版里全要卸掉(颜色留着) */
.code-pane :deep(pre code) { display: block; background: none; padding: 0; overflow: visible; }
</style>
