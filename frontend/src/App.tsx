import { useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { getStats } from './api'
import { useAuth } from './auth'
import Dashboard from './pages/Dashboard'
import Sources from './pages/Sources'
import Runs from './pages/Runs'
import Changes from './pages/Changes'
import Reviews from './pages/Reviews'
import Regulations from './pages/Regulations'
import Subscriptions from './pages/Subscriptions'
import Notifications from './pages/Notifications'
import Login from './pages/Login'

const NAV = [
  { to: '/dashboard', label: '总览' },
  { to: '/sources', label: '来源管理' },
  { to: '/runs', label: '采集运行' },
  { to: '/regulations', label: '法规归并' },
  { to: '/changes', label: '变更对比' },
  { to: '/reviews', label: '复核 / 影响研判' },
  { to: '/subscriptions', label: '订阅' },
  { to: '/notifications', label: '通知' },
]

export default function App() {
  const { user, loading, isAdmin, logout } = useAuth()
  const location = useLocation()
  const [pending, setPending] = useState(0)
  const [unread, setUnread] = useState(0)

  const refresh = () => {
    if (!user) return
    getStats()
      .then((s) => {
        setPending(s.pending_reviews)
        setUnread(s.unread_notifications)
      })
      .catch(() => {})
  }

  useEffect(() => {
    refresh()
    const t = setInterval(refresh, 15000)
    return () => clearInterval(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user])

  if (location.pathname === '/login') return <Login />
  if (loading) return <div style={{ padding: 40 }}>加载中…</div>
  if (!user) return <Navigate to="/login" replace />

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>法规变更情报<br />与影响研判平台</h1>
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}
          >
            <span>{n.label}</span>
            {n.to === '/sources' && !isAdmin && <span className="badge badge-gray" style={{ marginLeft: 'auto', fontSize: 10 }}>只读</span>}
            {n.to === '/reviews' && pending > 0 && <span className="nav-badge">{pending}</span>}
            {n.to === '/notifications' && unread > 0 && <span className="nav-badge">{unread}</span>}
          </NavLink>
        ))}
        <div style={{ padding: '16px 20px', borderTop: '1px solid #1e293b', marginTop: 12, color: '#94a3b8', fontSize: 13 }}>
          <div style={{ color: '#fff' }}>{user.display_name || user.username}</div>
          <div style={{ marginTop: 2 }}>
            <span className={'badge ' + (isAdmin ? 'badge-amber' : 'badge-blue')}>
              {isAdmin ? '管理员' : '分析师'}
            </span>
          </div>
          <button className="btn btn-sm" style={{ marginTop: 10 }} onClick={logout}>退出登录</button>
        </div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="/runs" element={<Runs />} />
          <Route path="/regulations" element={<Regulations />} />
          <Route path="/changes" element={<Changes />} />
          <Route path="/reviews" element={<Reviews onChange={refresh} />} />
          <Route path="/subscriptions" element={<Subscriptions />} />
          <Route path="/notifications" element={<Notifications onChange={refresh} />} />
        </Routes>
      </main>
    </div>
  )
}
