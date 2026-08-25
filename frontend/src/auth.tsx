import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { clearToken, fetchMe, getToken, type AuthUser } from './api'

interface AuthCtx {
  user: AuthUser | null
  loading: boolean
  isAdmin: boolean
  setUser: (u: AuthUser | null) => void
  logout: () => void
}

const Ctx = createContext<AuthCtx>({
  user: null,
  loading: true,
  isAdmin: false,
  setUser: () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!getToken()) {
      setLoading(false)
      return
    }
    fetchMe()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false))
  }, [])

  const logout = () => {
    clearToken()
    setUser(null)
    location.href = '/login'
  }

  return (
    <Ctx.Provider value={{ user, loading, isAdmin: user?.role === 'admin', setUser, logout }}>
      {children}
    </Ctx.Provider>
  )
}

export const useAuth = () => useContext(Ctx)
