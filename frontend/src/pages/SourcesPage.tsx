import { useEffect, useState } from 'react'
import {
  App as AntdApp,
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd'
import { DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined, ThunderboltOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Source } from '../types'
import { FREQUENCY_LABELS, ORG_TYPE_LABELS } from '../constants'

const emptyForm = {
  name: '',
  org_type: 'regulator',
  base_url: '',
  homepage_url: '',
  frequency: 'daily',
  interval_minutes: 1440,
  enabled: true,
  respect_robots: true,
  allowed_paths: [] as string[],
  max_depth: 2,
  description: '',
}

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Source | null>(null)
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const { user } = useAuth()
  const navigate = useNavigate()
  const isAdmin = user?.role === 'admin'

  const load = async () => {
    setLoading(true)
    try {
      const resp = await api.get('/api/sources')
      setSources(resp.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const openCreate = () => {
    setEditing(null)
    form.setFieldsValue(emptyForm)
    setModalOpen(true)
  }

  const openEdit = (record: Source) => {
    setEditing(record)
    form.setFieldsValue({ ...record })
    setModalOpen(true)
  }

  const submit = async () => {
    const values = await form.validateFields()
    if (editing) {
      await api.patch(`/api/sources/${editing.id}`, values)
      message.success('来源已更新')
    } else {
      await api.post('/api/sources', values)
      message.success('来源已创建')
    }
    setModalOpen(false)
    load()
  }

  const toggleEnabled = async (record: Source, enabled: boolean) => {
    await api.patch(`/api/sources/${record.id}`, { enabled })
    message.success(enabled ? '来源已启用' : '来源已停用')
    load()
  }

  const remove = async (record: Source) => {
    await api.delete(`/api/sources/${record.id}`)
    message.success('来源已删除')
    load()
  }

  const triggerCrawl = async (record: Source) => {
    const hide = message.loading(`正在采集「${record.name}」...`, 0)
    try {
      const resp = await api.post(`/api/sources/${record.id}/crawl`)
      hide()
      const run = resp.data
      if (run.status === 'success') {
        message.success(`采集完成：页面 ${run.pages_fetched}，附件 ${run.attachments_fetched}，发现变更 ${run.changes_detected}`)
      } else {
        message.warning(`采集结束，状态：${run.status}，请到采集运行页查看日志`)
      }
      load()
    } catch {
      hide()
      message.error('采集触发失败')
    }
  }

  const simulateUpdate = async () => {
    const resp = await api.post('/api/demo/simulate-update')
    message.success(resp.data.message)
  }

  const resetDemo = async () => {
    const resp = await api.post('/api/demo/reset')
    message.success(resp.data.message)
    load()
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card
        title="采集来源白名单"
        extra={
          <Space>
            {isAdmin && (
              <>
                <Button icon={<ThunderboltOutlined />} onClick={simulateUpdate}>
                  模拟法规修订（演示）
                </Button>
                <Popconfirm title="将演示站点恢复为初始版本？" onConfirm={resetDemo}>
                  <Button>重置演示站点</Button>
                </Popconfirm>
                <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
                  新增来源
                </Button>
              </>
            )}
            <Button icon={<ReloadOutlined />} onClick={load}>
              刷新
            </Button>
          </Space>
        }
      >
        <Typography.Paragraph type="secondary">
          管理员在此维护允许采集的监管网站、行业协会与公开征求意见页面。系统仅采集白名单路径前缀内、同源的公开页面，
          并严格遵守目标站点 robots.txt 规则；抓取频率按配置由 Celery Beat 定时调度。
        </Typography.Paragraph>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={sources}
          pagination={false}
          columns={[
            { title: 'ID', dataIndex: 'id', width: 60 },
            {
              title: '来源名称',
              dataIndex: 'name',
              render: (text: string, row: Source) => (
                <Space direction="vertical" size={0}>
                  <Typography.Text strong>{text}</Typography.Text>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {row.base_url}
                  </Typography.Text>
                </Space>
              ),
            },
            {
              title: '类型',
              dataIndex: 'org_type',
              width: 110,
              render: (v: string) => <Tag color="blue">{ORG_TYPE_LABELS[v] ?? v}</Tag>,
            },
            {
              title: '抓取频率',
              dataIndex: 'frequency',
              width: 110,
              render: (v: string, row: Source) => (
                <Space direction="vertical" size={0}>
                  <Tag>{FREQUENCY_LABELS[v] ?? v}</Tag>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    每{row.interval_minutes}分钟
                  </Typography.Text>
                </Space>
              ),
            },
            {
              title: '合规配置',
              width: 200,
              render: (_, row) => (
                <Space direction="vertical" size={2}>
                  <Space size={4}>
                    <Tag color={row.respect_robots ? 'green' : 'red'}>
                      robots {row.respect_robots ? '遵守' : '忽略'}
                    </Tag>
                    <Tag>深度 {row.max_depth}</Tag>
                  </Space>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    路径白名单：{row.allowed_paths.join('、') || '同源全部'}
                  </Typography.Text>
                </Space>
              ),
            },
            {
              title: '状态',
              dataIndex: 'enabled',
              width: 100,
              render: (enabled: boolean, row: Source) =>
                isAdmin ? (
                  <Switch checked={enabled} checkedChildren="启用" unCheckedChildren="停用" onChange={(v) => toggleEnabled(row, v)} />
                ) : (
                  <Tag color={enabled ? 'green' : 'default'}>{enabled ? '启用' : '停用'}</Tag>
                ),
            },
            {
              title: '上次采集',
              dataIndex: 'last_crawled_at',
              width: 160,
              render: (v: string | null) => (v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '从未采集'),
            },
            {
              title: '操作',
              width: 260,
              render: (_, row) => (
                <Space>
                  <Button size="small" type="primary" ghost icon={<ThunderboltOutlined />} onClick={() => triggerCrawl(row)}>
                    立即采集
                  </Button>
                  <Button size="small" onClick={() => navigate(`/runs?source=${row.id}`)}>
                    运行记录
                  </Button>
                  {isAdmin && (
                    <>
                      <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)} />
                      <Popconfirm title="删除该来源及其全部采集数据？" onConfirm={() => remove(row)}>
                        <Button size="small" danger icon={<DeleteOutlined />} />
                      </Popconfirm>
                    </>
                  )}
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editing ? '编辑采集来源' : '新增采集来源'}
        open={modalOpen}
        onOk={submit}
        onCancel={() => setModalOpen(false)}
        width={640}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="来源名称" rules={[{ required: true, message: '请输入来源名称' }]}>
            <Input placeholder="如：国家金融监督管理总局" />
          </Form.Item>
          <Form.Item name="org_type" label="机构类型" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'regulator', label: '监管机构' },
                { value: 'association', label: '行业协会' },
                { value: 'consultation', label: '公开征求意见' },
                { value: 'platform', label: '转载平台' },
              ]}
            />
          </Form.Item>
          <Form.Item name="base_url" label="站点根地址（同源校验依据）" rules={[{ required: true, message: '请输入根地址' }]}>
            <Input placeholder="https://example.gov.cn/" />
          </Form.Item>
          <Form.Item name="homepage_url" label="采集入口页（栏目首页）" rules={[{ required: true, message: '请输入入口页地址' }]}>
            <Input placeholder="https://example.gov.cn/policy/index.html" />
          </Form.Item>
          <Space size={16}>
            <Form.Item name="frequency" label="抓取频率">
              <Select
                style={{ width: 140 }}
                options={Object.entries(FREQUENCY_LABELS).map(([value, label]) => ({ value, label }))}
              />
            </Form.Item>
            <Form.Item name="interval_minutes" label="调度间隔（分钟）">
              <InputNumber min={5} max={43200} />
            </Form.Item>
            <Form.Item name="max_depth" label="抓取深度">
              <InputNumber min={0} max={5} />
            </Form.Item>
          </Space>
          <Form.Item name="allowed_paths" label="允许采集的路径前缀白名单">
            <Select mode="tags" placeholder="如 /policy/ （留空表示同源全部允许）" tokenSeparators={[',', ' ']} />
          </Form.Item>
          <Space size={32}>
            <Form.Item name="respect_robots" label="遵守 robots.txt" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="enabled" label="启用" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>
          <Form.Item name="description" label="备注说明">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}
