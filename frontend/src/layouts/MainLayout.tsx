import { useState } from 'react';
import { Layout, Menu, Badge, Avatar, Dropdown } from 'antd';
import {
  DashboardOutlined,
  GlobalOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  DiffOutlined,
  AuditOutlined,
  AlertOutlined,
  BellOutlined,
  SettingOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';

const { Header, Sider, Content } = Layout;

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '仪表盘',
    },
    {
      key: '/sources',
      icon: <GlobalOutlined />,
      label: '来源管理',
    },
    {
      key: '/crawl-runs',
      icon: <ThunderboltOutlined />,
      label: '采集运行',
    },
    {
      key: '/regulations',
      icon: <FileTextOutlined />,
      label: '法规库',
    },
    {
      key: '/changes',
      icon: <DiffOutlined />,
      label: '变更对比',
    },
    {
      key: '/reviews',
      icon: <AuditOutlined />,
      label: '复核队列',
    },
    {
      key: '/impact',
      icon: <AlertOutlined />,
      label: '影响研判',
    },
    {
      key: '/subscriptions',
      icon: <BellOutlined />,
      label: '订阅通知',
    },
    {
      key: '/notifications',
      icon: <Badge count={0} size="small"><BellOutlined /></Badge>,
      label: '消息中心',
    },
  ];

  const userMenuItems = [
    { key: 'profile', icon: <UserOutlined />, label: '个人信息' },
    { key: 'settings', icon: <SettingOutlined />, label: '设置' },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
        width={220}
      >
        <div className="sidebar-logo">
          {!collapsed ? '法规变更情报平台' : '法规'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{
          padding: '0 24px',
          background: '#fff',
          display: 'flex',
          justifyContent: 'flex-end',
          alignItems: 'center',
          borderBottom: '1px solid #f0f0f0',
        }}>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Avatar size="small" icon={<UserOutlined />} />
              <span>合规分析师</span>
            </div>
          </Dropdown>
        </Header>
        <Content style={{ margin: 0, minHeight: 280 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
