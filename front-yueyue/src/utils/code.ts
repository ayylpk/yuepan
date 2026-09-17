/** 代码页 / 资料页共用:按文件名猜 highlight.js 语言。
 *  表就一份,两边别再各自养(9/17 资料预览收编时从 CodeView 挪过来)。 */

const LANG_BY_EXT: Record<string, string> = {
  ts: 'typescript', js: 'javascript', vue: 'xml', json: 'json', py: 'python',
  java: 'java', css: 'css', scss: 'scss', html: 'xml', md: 'markdown',
  yml: 'yaml', yaml: 'yaml', xml: 'xml', sql: 'sql', sh: 'bash', rs: 'rust', go: 'go',
}

/** 路径/文件名 → hljs 语言名;认不出返回 undefined(调用方走纯文本兜底) */
export function langOf(name: string | undefined): string | undefined {
  if (!name) return undefined
  const ext = name.split('.').pop()?.toLowerCase() ?? ''
  return LANG_BY_EXT[ext]
}
