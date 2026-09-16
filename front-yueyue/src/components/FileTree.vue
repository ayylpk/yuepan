<script setup lang="ts">
// 递归文件树:<details>/<summary> 原生折叠,零 JS 状态。
// props.node 是构建好的树,由 CodeView 从 git ls-files 的平铺路径拼出来。
export interface TreeNode {
  name: string
  path: string
  children?: TreeNode[] // 有=目录,没有=文件
}

defineProps<{ node: TreeNode }>()
const emit = defineEmits<{ pick: [path: string] }>()
</script>

<template>
  <details v-if="node.children" class="dir" :open="node.path === ''">
    <summary>{{ node.name || '根' }}<span class="cnt">{{ node.children.length }}</span></summary>
    <div class="kids">
      <FileTree v-for="c in node.children" :key="c.path" :node="c" @pick="(p) => emit('pick', p)" />
    </div>
  </details>
  <button v-else class="file" @click="emit('pick', node.path)">{{ node.name }}</button>
</template>

<style scoped>
.dir { margin: 0; }
summary {
  cursor: pointer; padding: 3px 6px; border-radius: 6px;
  font-size: 13.5px; color: var(--ink); user-select: none;
  list-style: none; display: flex; align-items: center; gap: 6px;
}
summary::before { content: '▸'; color: var(--sea-deep); transition: transform 0.15s; }
details[open] > summary::before { transform: rotate(90deg); }
summary:hover { background: var(--cloud); }
.cnt { font-size: 11px; color: var(--ink-soft); }
.kids { padding-left: 14px; border-left: 1px dashed var(--line); margin-left: 9px; }
.file {
  display: block; width: 100%; text-align: left; border: none; background: none;
  padding: 3px 6px; border-radius: 6px; cursor: pointer;
  font-size: 13px; font-family: var(--font-mono); color: var(--ink-soft);
}
.file:hover { background: var(--cloud); color: var(--ink); }
</style>
