import type {
  NodesResponse,
  StatusResponse,
  GatewayConfig,
} from './types'

const BASE = ''
const TOKEN_KEY = 'vsg_token'
const USER_KEY = 'vsg_user'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string, username: string) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, username)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function isLoggedIn(): boolean {
  return !!localStorage.getItem(TOKEN_KEY)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (token) {
    headers['Authorization'] = 'Bearer ' + token
  }
  const res = await fetch(BASE + path, {
    ...init,
    headers: {
      ...headers,
      ...(init?.headers as Record<string, string> ?? {}),
    },
  })
  if (res.status === 401) {
    clearToken()
    throw new Error('未登录或登录已过期')
  }
  if (!res.ok) {
    let msg = 'HTTP ' + res.status
    try {
      const body = await res.json()
      if (body?.error) msg = body.error
    } catch {
      /* ignore */
    }
    throw new Error(msg)
  }
  return res.json() as Promise<T>
}

export const api = {
  login(username: string, password: string): Promise<{ ok: boolean; token: string; username: string }> {
    return request<{ ok: boolean; token: string; username: string }>('/api/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
  },

  getNodes(params?: { country?: string; reachable?: boolean }): Promise<NodesResponse> {
    const q = new URLSearchParams()
    if (params?.country) q.set('country', params.country)
    if (params?.reachable) q.set('reachable', params.reachable ? '1' : '0')
    const qs = q.toString()
    return request<NodesResponse>('/api/nodes' + (qs ? '?' + qs : ''))
  },

  getCountries(): Promise<Record<string, number>> {
    return request<Record<string, number>>('/api/countries')
  },

  getStatus(): Promise<StatusResponse> {
    return request<StatusResponse>('/api/status')
  },

  getConfig(): Promise<GatewayConfig> {
    return request<GatewayConfig>('/api/config')
  },

  refreshNodes(): Promise<{ ok: boolean; total: number }> {
    return request<{ ok: boolean; total: number }>('/api/refresh', { method: 'POST' })
  },

  selectNode(nodeId: string, action: 'add' | 'remove' | 'toggle' = 'toggle'): Promise<{ ok: boolean; selected: string[] }> {
    return request<{ ok: boolean; selected: string[] }>('/api/select', {
      method: 'POST',
      body: JSON.stringify({ node_id: nodeId, action }),
    })
  },

  selectCountry(country: string, limit = 3): Promise<{ ok: boolean; selected: string[] }> {
    return request<{ ok: boolean; selected: string[] }>('/api/select', {
      method: 'POST',
      body: JSON.stringify({ country, limit }),
    })
  },

  updateConfig(data: Partial<Record<string, unknown>>): Promise<{ ok: boolean; config: GatewayConfig }> {
    return request<{ ok: boolean; config: GatewayConfig }>('/api/config', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  reconnectAll(): Promise<{ ok: boolean }> {
    return request<{ ok: boolean }>('/api/reconnect', { method: 'POST' })
  },

  getLogs(): Promise<{ time: string; level: string; message: string }[]> {
    return request<{ time: string; level: string; message: string }[]>('/api/logs')
  },
}
