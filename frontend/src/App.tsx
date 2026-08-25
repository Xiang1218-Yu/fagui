import { useEffect, useState } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import {
  AppstoreOutlined,
  BellOutlined,
  CheckSquareOutlined,
  CloudSyncOutlined,
  ExperimentOutlined,
  FileSearchOutlined,
  GlobalOutlined,
  LogoutOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons'
import { Badge, Dropdown, Layout, Menu, Popover, Spin, Tag, Typography } from 'antd'
import { api } from './api/client'
import { useAuth } from './auth/AuthContext'
import type { NotificationItem } from './types'

import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import SourcesPage from './pages/SourcesPage'
import CrawlRunsPage from './pages/CrawlRunsPage'
import RegulationsPage from './pages/RegulationsPage'
import ChangesPage from './pages/ChangesPage'
import ReviewPage from './pages/ReviewPage'
import ImpactPage from './pages/ImpactPage'
import SubscriptionsPage from './pages/SubscriptionsPage'

const { Sider, Header, Content } = Layout

const MENU_ITEMS = [
  { key: '/dashboard', icon: <AppstoreOutlined />, label: <Link to="/dashboard">情报看板</Link> },
  { key: '/sources', icon: <GlobalOutlined />, label: <Link to="/sources">来源管理</Link> },
  { key: '/runs', icon: <CloudSyncOutlined />, label: <Link to="/runs">采集运行</Link> },
  { key: '/regulations', icon: <FileSearchOutlined />, label: <Link to="/regulations">法规库</Link> },
  { key: '/changes', icon: <SafetyCertificateOutlined />, label: <Link to="/changes">变更对比</Link> },
  { key: '/review', icon: <CheckSquareOutlined />, label: <Link to="/review">复核队列</Link> },
  { key: '/impact', icon: <ExperimentOutlined />, label: <Link to="/impact">影响研判</Link> },
  { key: '/subscriptions', icon: <BellOutlined />, label: <Link to="/subscriptions">订阅通知</Link> },
]

const EVENT_LABELS: Record<string, string> = {
  change_detected: '法规变更',
  review_decided: '复核结论',
  impact_published: '研判发布',
}

function NotificationBell() {
  const [unread, setUnread] = useState(0)
  const [items, setItems] = useState<NotificationItem[]>([])
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [countResp, listResp] = await Promise.all([
        api.get('/api/notifications/unread-count'),
        api.get('/api/notifications?unread_only=true'),
      ])
      setUnread(countResp.data.unread)
      setItems(listResp.data.slice(0, 8))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 30000)
    return () => clearInterval(timer)
  }, [])

  const markAll = async () => {
    await api.post('/api/notifications/read-all')
    load()
  }

  const content = (
    <div style={{ width: 360, maxHeight: 420, overflow: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <Typography.Text strong>未读通知</Typography.Text>
        <a onClick={markAll}>全部已读</a>
      </div>
      <Spin spinning={loading}>
        {items.length === 0 && <Typography.Text type="secondary">暂无未读通知</Typography.Text>}
        {items.map((n) => (
          <div
            key={n.id}
            style={{ padding: '8px 0', borderBottom: '1px solid #f5f5f5' }}
          >
            <Tag color="blue" style={{ marginRight: 4 }}>
              {EVENT_LABELS[n.event_type] ?? n.event_type}
            </Tag>
            <Typography.Text strong style={{ fontSize: 13 }}>
              {n.title}
            </Typography.Text>
            <Typography.Paragraph
              type="secondary"
              style={{ fontSize: 12, margin: '4px 0 0', whiteSpace: 'pre-wrap' }}
              ellipsis={{ rows: 2 }}
            >
              {n.body}
            </Typography.Paragraph>
          </div>
        ))}
      </Spin>
    </div>
  )

  return (
    <Popover content={content} trigger="click" placement="bottomRight" onOpenChange={(open) => open && load()}>
      <Badge count={unread} size="small">
        <BellOutlined style={{ fontSize: 18, color: '#fff', cursor: 'pointer' }} />
      </Badge>
    </Popover>
  )
}

function MainLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const selectedKey = '/' + (location.pathname.split('/')[1] || 'dashboard')

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={210} theme="dark" breakpoint="lg" collapsedWidth={0}>
        <div
          style={{
            height: 56,
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 700,
            fontSize: 15,
            letterSpacing: 1,
            margin: '8px 12px',
            lineHeight: 1.3,
            textAlign: 'center',
          }}
        >
          法规变更情报
          <br />
          与影响研判平台
        </div>
        <Menu theme="dark" mode="inline" selectedKeys={[selectedKey]} items={MENU_ITEMS} />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            boxShadow: '0 1px 4px rgba(0,21,41,.08)',
          }}
        >
          <Typography.Text strong style={{ fontSize: 15 }}>
            {MENU_ITEMS.find((m) => m.key === selectedKey)
              ? MENU_ITEMS.find((m) => m.key === selectedKey)!.key === '/dashboard'
                ? '情报看板'
                : null
              : null}
          </Typography.Text>
          <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
            <NotificationBell />
            <Dropdown
              menu={{
                items: [
                  {
                    key: 'logout',
                    icon: <LogoutOutlined />,
                    label: '退出登录',
                    onClick: () => {
                      logout()
                      navigate('/login')
                    },
                  },
                ],
              }}
            >
              <span style={{ cursor: 'pointer', color: '#333' }}>
                <Tag color={user?.role === 'admin' ? 'gold' : 'geekblue'}>
                  {user?.role === 'admin' ? '管理员' : '分析师'}
                </Tag>
                {user?.display_name}
              </span>
            </Dropdown>
          </div>
        </Header>
        <Content style={{ margin: 16 }}>{children}</Content>
      </Layout>
    </Layout>
  )
}

function Protected({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  if (!user) {
    return <Navigate to="/login" replace />
  }
  return <MainLayout>{children}</MainLayout>
}

export default function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route
          path="/dashboard"
          element={
            <Protected>
              <DashboardPage />
            </Protected>
          }
        />
        <Route
          path="/sources"
          element={
            <Protected>
              <SourcesPage />
            </Protected>
          }
        />
        <Route
          path="/runs"
          element={
            <Protected>
              <CrawlRunsPage />
            </Protected>
          }
        />
        <Route
          path="/regulations"
          element={
            <Protected>
              <RegulationsPage />
            </Protected>
          }
        />
        <Route
          path="/changes"
          element={
            <Protected>
              <ChangesPage />
            </Protected>
          }
        />
        <Route
          path="/review"
          element={
            <Protected>
              <ReviewPage />
            </Protected>
          }
        />
        <Route
          path="/impact"
          element={
            <Protected>
              <ImpactPage />
            </Protected>
          }
        />
        <Route
          path="/subscriptions"
          element={
            <Protected>
              <SubscriptionsPage />
            </Protected>
          }
        />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
