import { ReactNode } from 'react'
import { NavLink, Navigate, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { api, clearToken, getToken } from './api/client'
import { roleLabel, useCurrentUser } from './types'
import SourcesPage from './pages/SourcesPage'
import RunsPage from './pages/RunsPage'
import ChangesPage from './pages/ChangesPage'
import ChangeDetailPage from './pages/ChangeDetailPage'
import ImpactPage from './pages/ImpactPage'
import ReviewPage from './pages/ReviewPage'
import SubscriptionsPage from './pages/SubscriptionsPage'
import LoginPage from './pages/LoginPage'
import UsersPage from './pages/UsersPage'

const navItems = [
  { to: '/sources', label: '来源管理' },
  { to: '/runs', label: '采集运行' },
  { to: '/changes', label: '变更对比' },
  { to: '/impact', label: '影响研判' },
  { to: '/review', label: '复核队列' },
  { to: '/subscriptions', label: '订阅通知' },
]

function RequireAuth({ children }: { children: ReactNode }) {
  const location = useLocation()
  if (!getToken()) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  }
  return <>{children}</>
}

function AdminOnly({ children }: { children: ReactNode }) {
  const user = useCurrentUser()
  if (user?.role !== 'admin') {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}

function Layout() {
  const user = useCurrentUser()
  const navigate = useNavigate()

  const handleLogout = async () => {
    try {
      await api('/auth/logout', { method: 'POST' })
    } catch {
      // 忽略注销接口异常，本地状态照常清理
    }
    clearToken()
    navigate('/login', { replace: true })
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-title">法规变更情报平台</div>
        <nav>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
            >
              {item.label}
            </NavLink>
          ))}
          {user?.role === 'admin' && (
            <NavLink to="/users" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
              用户管理
            </NavLink>
          )}
        </nav>
        <div className="sidebar-user">
          {user && (
            <div className="sidebar-user-info">
              <span className="sidebar-username">{user.username}</span>
              <span className={`badge badge-role-${user.role}`}>{roleLabel[user.role]}</span>
            </div>
          )}
          <button className="btn small sidebar-logout" onClick={handleLogout}>退出登录</button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Navigate to="/sources" replace />} />
        <Route path="/sources" element={<SourcesPage />} />
        <Route path="/runs" element={<RunsPage />} />
        <Route path="/changes" element={<ChangesPage />} />
        <Route path="/changes/:id" element={<ChangeDetailPage />} />
        <Route path="/impact" element={<ImpactPage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/subscriptions" element={<SubscriptionsPage />} />
        <Route
          path="/users"
          element={
            <AdminOnly>
              <UsersPage />
            </AdminOnly>
          }
        />
      </Route>
    </Routes>
  )
}
