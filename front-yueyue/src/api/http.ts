/** fetch 薄封装:JSON 同构接口一个 get/post/put/del 打通。
 *  - 自动带 cookie(同源默认 credentials:same-origin,HttpOnly session 靠它)
 *  - 非 2xx 统一抛 ApiError,消息用后端 detail,页面只管展示
 *  - 401 = 会话过期,直接轰回登录页(带 redirect 回跳)
 */

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

type Body = Record<string, unknown> | unknown[] | undefined

async function request<T>(method: string, path: string, body?: Body): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (res.status === 401 && !location.pathname.startsWith('/login')) {
    location.assign('/login?redirect=' + encodeURIComponent(location.pathname))
    throw new ApiError(401, '登录已过期,请重新登录')
  }
  if (!res.ok) {
    let detail = `请求失败(${res.status})`
    try {
      const data = (await res.json()) as { detail?: unknown }
      if (typeof data?.detail === 'string') detail = data.detail
    } catch { /* 非 json 错误体就用状态码 */ }
    throw new ApiError(res.status, detail)
  }
  const payload = (await res.json()) as unknown
  // Result 信封自动拆包:{code,message,data} → data(后端 back-yueyue README 约定);
  // PageResult {count,data} 没有 code 字段,原样返回给调用方拿 count。
  if (payload && typeof payload === 'object' && 'code' in payload) {
    const envelope = payload as { code: number; message?: string; data: unknown }
    if (envelope.code !== 200) throw new ApiError(envelope.code, envelope.message || '后端返回失败')
    return envelope.data as T
  }
  return payload as T
}

export const http = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: Body) => request<T>('POST', path, body),
  put: <T>(path: string, body?: Body) => request<T>('PUT', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),
}

/** multipart 上传专用(photo 上传的表单不套 JSON) */
export async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(path, { method: 'POST', body: form })
  if (!res.ok) {
    let detail = `上传失败(${res.status})`
    try {
      const data = await res.json()
      if (typeof data?.detail === 'string') detail = data.detail
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail)
  }
  return (await res.json()) as T
}
