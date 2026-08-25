import { useEffect, useState } from 'react'
import {
  App as AntdApp,
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd'
import { DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { api } from '../api/client'
import type { NotificationItem, Source, Subscription } from '../types'
import { EVENT_TYPE_LABELS } from '../constants'

export default function SubscriptionsPage() {
  const [subs, setSubs] = useState<Subscription[]>([])
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [sources, setSources] = useState<Source[]>([])
  const [options, setOptions] = useState<{ channels: { value: string; label: string }[]; event_types: { value: string; label: string }[] }>({
    channels: [],
    event_types: [],
  })
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Subscription | null>(null)
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()

  const load = async () => {
    setLoading(true)
    try {
      const [subsResp, notifResp, sourcesResp, optsResp] = await Promise.all([
        api.get('/api/subscriptions'),
        api.get('/api/notifications'),
        api.get('/api/sources'),
        api.get('/api/subscriptions/meta/options'),
      ])
      setSubs(subsResp.data)
      setNotifications(notifResp.data)
      setSources(sourcesResp.data)
      setOptions(optsResp.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({
      channel: 'inapp',
      event_types: ['change_detected'],
      source_ids: [],
      keywords: [],
      enabled: true,
    })
    setModalOpen(true)
  }

  const openEdit = (record: Subscription) => {
    setEditing(record)
    form.setFieldsValue({ ...record })
    setModalOpen(true)
  }

  const submit = async () => {
    const values = await form.validateFields()
    if (editing) {
      await api.patch(`/api/subscriptions/${editing.id}`, values)
      message.success('订阅已更新')
    } else {
      await api.post('/api/subscriptions', values)
      message.success('订阅已创建')
    }
    setModalOpen(false)
    load()
  }

  const remove = async (record: Subscription) => {
    await api.delete(`/api/subscriptions/${record.id}`)
    message.success('订阅已删除')
    load()
  }

  const markRead = async (record: NotificationItem) => {
    await api.post(`/api/notifications/${record.id}/read`)
    load()
  }

  const markAllRead = async () => {
    await api.post('/api/notifications/read-all')
    message.success('已全部标记为已读')
    load()
  }

  return (
    <Card>
      <Tabs
        defaultActiveKey="subs"
        items={[
          {
            key: 'subs',
            label: '订阅规则',
            children: (
              <>
                <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
                  <Typography.Text type="secondary">
                    按事件类型、来源与关键词订阅法规动态；站内通知实时到达，邮件/Webhook 渠道在本环境中模拟投递并留存记录。
                  </Typography.Text>
                  <Space>
                    <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
                      新建订阅
                    </Button>
                    <Button icon={<ReloadOutlined />} onClick={load}>
                      刷新
                    </Button>
                  </Space>
                </Space>
                <Table
                  rowKey="id"
                  loading={loading}
                  dataSource={subs}
                  pagination={false}
                  columns={[
                    { title: 'ID', dataIndex: 'id', width: 60 },
                    { title: '订阅名称', dataIndex: 'name' },
                    {
                      title: '渠道',
                      dataIndex: 'channel',
                      width: 120,
                      render: (v: string) => (
                        <Tag color={v === 'inapp' ? 'blue' : v === 'email' ? 'green' : 'purple'}>
                          {options.channels.find((c) => c.value === v)?.label ?? v}
                        </Tag>
                      ),
                    },
                    {
                      title: '事件',
                      dataIndex: 'event_types',
                      width: 220,
                      render: (types: string[]) =>
                        types.map((t) => <Tag key={t}>{EVENT_TYPE_LABELS[t] ?? t}</Tag>),
                    },
                    {
                      title: '来源过滤',
                      dataIndex: 'source_ids',
                      width: 180,
                      render: (ids: number[]) =>
                        ids.length === 0 ? (
                          <Typography.Text type="secondary">全部来源</Typography.Text>
                        ) : (
                          ids.map((id) => <Tag key={id}>{sources.find((s) => s.id === id)?.name ?? `#${id}`}</Tag>)
                        ),
                    },
                    {
                      title: '关键词',
                      dataIndex: 'keywords',
                      width: 180,
                      render: (kws: string[]) =>
                        kws.length === 0 ? <Typography.Text type="secondary">不限</Typography.Text> : kws.map((k) => <Tag key={k}>{k}</Tag>),
                    },
                    {
                      title: '启用',
                      dataIndex: 'enabled',
                      width: 80,
                      render: (v: boolean) => <Switch checked={v} disabled />,
                    },
                    {
                      title: '操作',
                      width: 120,
                      render: (_: unknown, record: Subscription) => (
                        <Space>
                          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)} />
                          <Popconfirm title="删除该订阅？" onConfirm={() => remove(record)}>
                            <Button size="small" danger icon={<DeleteOutlined />} />
                          </Popconfirm>
                        </Space>
                      ),
                    },
                  ]}
                />
              </>
            ),
          },
          {
            key: 'inbox',
            label: '通知中心',
            children: (
              <>
                <Space style={{ marginBottom: 16 }}>
                  <Button onClick={markAllRead}>全部已读</Button>
                  <Button icon={<ReloadOutlined />} onClick={load}>
                    刷新
                  </Button>
                </Space>
                <Table
                  rowKey="id"
                  loading={loading}
                  dataSource={notifications}
                  pagination={{ pageSize: 15 }}
                  rowClassName={(record) => (record.is_read ? '' : 'unread-row')}
                  columns={[
                    {
                      title: '状态',
                      dataIndex: 'is_read',
                      width: 90,
                      render: (read: boolean) => (read ? <Tag>已读</Tag> : <Tag color="red">未读</Tag>),
                    },
                    {
                      title: '事件',
                      dataIndex: 'event_type',
                      width: 130,
                      render: (v: string) => <Tag color="blue">{EVENT_TYPE_LABELS[v] ?? v}</Tag>,
                    },
                    { title: '标题', dataIndex: 'title', width: 320 },
                    {
                      title: '内容',
                      dataIndex: 'body',
                      render: (text: string) => (
                        <Typography.Text style={{ whiteSpace: 'pre-wrap' }} type="secondary">
                          {text}
                        </Typography.Text>
                      ),
                    },
                    {
                      title: '投递',
                      dataIndex: 'send_status',
                      width: 90,
                      render: (v: string) => (v === 'simulated' ? <Tag color="orange">模拟</Tag> : <Tag color="green">已送达</Tag>),
                    },
                    {
                      title: '时间',
                      dataIndex: 'created_at',
                      width: 160,
                      render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm'),
                    },
                    {
                      title: '操作',
                      width: 90,
                      render: (_: unknown, record: NotificationItem) =>
                        record.is_read ? null : (
                          <Button size="small" onClick={() => markRead(record)}>
                            已读
                          </Button>
                        ),
                    },
                  ]}
                />
              </>
            ),
          },
        ]}
      />

      <Modal
        title={editing ? '编辑订阅' : '新建订阅'}
        open={modalOpen}
        onOk={submit}
        onCancel={() => setModalOpen(false)}
        width={560}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="订阅名称" rules={[{ required: true, message: '请输入订阅名称' }]}>
            <Input placeholder="如：数据合规类法规变更" />
          </Form.Item>
          <Form.Item name="channel" label="通知渠道" rules={[{ required: true }]}>
            <Select options={options.channels} />
          </Form.Item>
          <Form.Item name="event_types" label="订阅事件" rules={[{ required: true, message: '至少选择一个事件' }]}>
            <Checkbox.Group
              options={options.event_types.map((e) => ({ label: e.label, value: e.value }))}
            />
          </Form.Item>
          <Form.Item name="source_ids" label="来源范围（不选表示全部来源）">
            <Select
              mode="multiple"
              placeholder="全部来源"
              options={sources.map((s) => ({ value: s.id, label: s.name }))}
            />
          </Form.Item>
          <Form.Item name="keywords" label="关键词过滤（命中任一即通知）">
            <Select mode="tags" placeholder="如：数据合规、跨境、个人信息" tokenSeparators={[',', '，']} />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.channel !== cur.channel}>
            {({ getFieldValue }) =>
              getFieldValue('channel') === 'email' ? (
                <Form.Item name="destination" label="接收邮箱" rules={[{ required: true, message: '请输入邮箱' }]}>
                  <Input placeholder="analyst@example.com" />
                </Form.Item>
              ) : getFieldValue('channel') === 'webhook' ? (
                <Form.Item name="destination" label="Webhook 地址" rules={[{ required: true, message: '请输入地址' }]}>
                  <Input placeholder="https://example.com/hook" />
                </Form.Item>
              ) : null
            }
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
