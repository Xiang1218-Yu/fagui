import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import SourcesPage from './pages/SourcesPage'
import RunsPage from './pages/RunsPage'
import ChangesPage from './pages/ChangesPage'
import ChangeDetailPage from './pages/ChangeDetailPage'
import ImpactPage from './pages/ImpactPage'
import ReviewPage from './pages/ReviewPage'
import SubscriptionsPage from './pages/SubscriptionsPage'

const navItems = [
  { to: '/sources', label: '来源管理' },
  { to: '/runs', label: '采集运行' },
  { to: '/changes', label: '变更对比' },
  { to: '/impact', label: '影响研判' },
  { to: '/review', label: '复核队列' },
  { to: '/subscriptions', label: '订阅通知' },
]

export default function App() {
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
        </nav>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/sources" replace />} />
          <Route path="/sources" element={<SourcesPage />} />
          <Route path="/runs" element={<RunsPage />} />
          <Route path="/changes" element={<ChangesPage />} />
          <Route path="/changes/:id" element={<ChangeDetailPage />} />
          <Route path="/impact" element={<ImpactPage />} />
          <Route path="/review" element={<ReviewPage />} />
          <Route path="/subscriptions" element={<SubscriptionsPage />} />
        </Routes>
      </main>
    </div>
  )
}
