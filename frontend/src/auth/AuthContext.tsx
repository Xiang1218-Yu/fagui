import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { api } from '../api/client'
import type { UserInfo } from '../types'

interface AuthState {
  user: UserInfo | null
  login: (username: string, password: string) => Promise<UserInfo>
  logout: () => void
}

const AuthContext = createContext<AuthState>({
  user: null,
  login: async () => {
    throw new Error('not ready')
  },
  logout: () => undefined,
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(() => {
    const raw = localStorage.getItem('fagui_user')
    return raw ? (JSON.parse(raw) as UserInfo) : null
  })

  const value = useMemo<AuthState>(
    () => ({
      user,
      login: async (username: string, password: string) => {
        const resp = await api.post('/api/auth/login', { username, password })
        const { access_token, user: userInfo } = resp.data
        localStorage.setItem('fagui_token', access_token)
        localStorage.setItem('fagui_user', JSON.stringify(userInfo))
        setUser(userInfo)
        return userInfo as UserInfo
      },
      logout: () => {
        localStorage.removeItem('fagui_token')
        localStorage.removeItem('fagui_user')
        setUser(null)
        window.location.href = '/login'
      },
    }),
    [user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
