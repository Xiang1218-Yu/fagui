const BASE_URL = '/api'
const TOKEN_KEY = 'regintel_token'
const USER_KEY = 'regintel_user'

let token: string | null = localStorage.getItem(TOKEN_KEY)

export function setToken(t: string) {
  token = t
  localStorage.setItem(TOKEN_KEY, t)
}

export function getToken(): string | null {
  return token
}

export function clearToken() {
  token = null
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

async function readDetail(res: Response): Promise<string | null> {
  try {
    const data = await res.json()
    if (data && data.detail) {
      return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
    }
  } catch {
    // 忽略解析失败
  }
  return null
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) }
  if (options.body && typeof options.body === 'string') {
    headers['Content-Type'] = 'application/json'
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  if (res.status === 401) {
    const detail = await readDetail(res)
    // 登录页自身的 401（如密码错误）不跳转，由页面展示错误
    if (window.location.pathname !== '/login') {
      clearToken()
      window.location.href = '/login'
    }
    throw new Error(detail ?? '登录状态无效，请重新登录')
  }
  if (res.status === 403) {
    const detail = await readDetail(res)
    // 后端要求先修改初始密码时，统一跳转到修改密码页
    if (detail && detail.includes('请先修改初始密码')) {
      if (window.location.pathname !== '/change-password') {
        window.location.href = '/change-password'
      }
      throw new Error(detail)
    }
    throw new Error(detail ? `权限不足：${detail}` : '权限不足')
  }
  if (!res.ok) {
    const detail = await readDetail(res)
    throw new Error(detail ?? `请求失败（${res.status}）`)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}
