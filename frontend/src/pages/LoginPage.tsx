import { useState } from 'react'
import { Button, Card, Form, Input, Typography, App as AntdApp, Alert, Space, Tag } from 'antd'
import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const { message } = AntdApp.useApp()
  const [loading, setLoading] = useState(false)

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      const user = await login(values.username, values.password)
      message.success(`欢迎，${user.display_name}`)
      navigate('/dashboard')
    } catch {
      message.error('登录失败：用户名或密码错误')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #1f5fa8 0%, #2b3a67 100%)',
      }}
    >
      <Card style={{ width: 420, boxShadow: '0 8px 30px rgba(0,0,0,.2)' }}>
        <Typography.Title level={3} style={{ textAlign: 'center', marginBottom: 4 }}>
          法规变更情报与影响研判平台
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ textAlign: 'center', marginBottom: 24 }}>
          监管来源采集 · 快照追溯 · 变更研判 · 闭环复核
        </Typography.Paragraph>
        <Form onFinish={onFinish} size="large" initialValues={{ username: 'admin', password: 'admin123' }}>
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              登录
            </Button>
          </Form.Item>
        </Form>
        <Alert
          type="info"
          showIcon
          message="演示账号"
          description={
            <Space direction="vertical" size={2}>
              <span>
                <Tag color="gold">管理员</Tag> admin / admin123（来源维护、采集配置、模拟修订）
              </span>
              <span>
                <Tag color="geekblue">分析师</Tag> analyst / analyst123（变更复核、影响研判、订阅）
              </span>
            </Space>
          }
        />
      </Card>
    </div>
  )
}
