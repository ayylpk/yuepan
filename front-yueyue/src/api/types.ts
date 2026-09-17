/** 前后端接口数据结构约定。
 *  Diary/Photo 对齐 back-yueyue 已实现接口(/api/diary、/api/photo,role:0=公开 1=隐私);
 *  其余是待实现接口的契约(前端先行,后端照抄)。
 */

export interface Diary {
  id: number
  title: string
  content: string
  role: number // 0=正常公开 1=隐私(小屋)
  created_at: string
  updated_at: string
}

/** 后端 PageResult[T] 原样(未拆包时有 count) */
export interface PageResult<T> {
  count: number
  data: T[]
}

/** 照片(后端 PhotoResponse 原样;path 字段后端刻意不回传,出图拼 /api/photo/{id}/file) */
export interface Photo {
  id: number
  type: string // 相册/分类标签,≤20 字,可空
  name: string // 原始文件名(展示用)
  role: number // 与日记统一用 role 口径:0=上墙 1=收进小屋
  size: number // 字节
  created_at: string
  updated_at: string
}

/** 资料(FileInfoResponse 原样)。9/17 口径:原名上盘,name 就是磁盘文件名(可 PUT 改名,
 *  磁盘同步 move);直览 GET /api/file/{id}/raw(图/文本/pdf),下载 /download,其余"请下载查看"。 */
export interface FileEntry {
  id: number
  name: string // 文件名(与磁盘一致,含 "(N)" 避让后缀)
  type: string // 小写扩展名,不带点(改名时后端跟着重算)
  role: number // 0=上架 1=收进小屋
  size: number // 字节
  created_at: string
  updated_at: string
}

export interface Project {
  id: number // 后端 int 主键(原契约猜的 string,以后端实现为准)
  name: string
  code: string // emoji 占位图标
  desc: string
  tech: string[]
  repo: string | null // 对应"在线看代码"白名单项;null=没挂本机目录
  period: string
  created_at: string
  updated_at: string
}

/** 编辑弹窗回显专用(GET /api/projects/{id}/manage,要登录才有多出来的 path) */
export interface ProjectManage extends Project {
  path: string
}

/** 技术栈字典项(GET /api/tech/list 与 /api/tech/page) */
export interface Tech {
  id: number
  name: string
  ref_count: number // 被几个项目引用,删除前一眼看清牵连
  created_at: string
}

export interface RepoInfo {
  name: string
  desc: string
  exists: boolean
  branch: string
  last_commit: string
}

export interface CommitInfo {
  hash: string
  subject: string
  author: string
  ago: string
}

export interface MeInfo {
  logged_in: boolean
  username?: string
  private?: boolean
}
