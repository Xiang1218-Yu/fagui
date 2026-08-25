import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import {
  App as AntdApp,
  Button,
  Card,
  Drawer,
  Form,
  Input,
  Radio,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd'
import { DeleteOutlined, PlusOutlined, ReloadOutlined, SendOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { api } from '../api/client'
import type { Change, ImpactAssessment } from '../types'
import { CHANGE_TYPE_LABELS, SEVERITY_COLORS } from '../constants'

export default function ImpactPage() {
  const [items, setItems] = useState<ImpactAssessment[]>([])
  const [changes, setChanges] = useState<Change[]>([])
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const location = useLocation()
  const presetChangeId = (location.state as { changeId?: number } | null)?.changeId

  const load = async () => {
    setLoading(true)
    try {
      const [assessResp, changesResp] = await Promise.all([
        api.get('/api/impact'),
        api.get('/api/changes'),
      ])
      setItems(assessResp.data)
      setChanges(changesResp.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const eligibleChanges = changes.filter(
    (c) => c.change_type !== 'title_modified' && c.status === 'confirmed',
  )

  useEffect(() => {
    if (!presetChangeId) return
    const target = changes.find((c) => c.id === presetChangeId)
    if (target && target.status !== 'confirmed') {
      message.warning('该变更尚未通过复核（待复核或已判误报），不能创建影响研判')
      return
    }
    form.setFieldsValue({ change_id: presetChangeId })
    setDrawerOpen(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presetChangeId, changes])

  const onSelectChange = (changeId: number) => {
    const change = changes.find((c) => c.id === changeId)
    if (change) {
      form.setFieldsValue({
        regulation_id: change.regulation_id ?? undefined,
        risk_level: change.severity ?? 'medium',
      })
    }
  }

  const submit = async (publish: boolean) => {
    const values = await form.validateFields()
    const payload = { ...values, status: publish ? 'published' : 'draft' }
    try {
      const resp = await api.post('/api/impact', payload)
      if (publish) {
        await api.post(`/api/impact/${resp.data.id}/publish`)
      }
      message.success(publish ? '影响研判已发布，订阅人已收到通知' : '草稿已保存')
      setDrawerOpen(false)
      form.resetFields()
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail ?? '保存失败，请检查该变更是否已通过复核')
    }
  }

  const publishExisting = async (record: ImpactAssessment) => {
    try {
      await api.post(`/api/impact/${record.id}/publish`)
      message.success('研判已发布')
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail ?? '发布失败')
    }
  }

  return (
    <Card
      title="影响研判"
      extra={
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              form.resetFields()
              if (presetChangeId) form.setFieldsValue({ change_id: presetChangeId })
              setDrawerOpen(true)
            }}
          >
            新建研判
          </Button>
          <Button icon={<ReloadOutlined />} onClick={load}>
            刷新
          </Button>
        </Space>
      }
    >
      <Typography.Paragraph type="secondary">
        针对已确认的法规变更，分析师评估受影响团队、业务条线与风险等级，登记行动项并发布给业务团队；每条研判关联具体变更与快照，结论来源可回溯。
      </Typography.Paragraph>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        pagination={{ pageSize: 15 }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          {
            title: '研判对象',
            dataIndex: 'regulation_title',
            render: (text: string, row: ImpactAssessment) => (
              <Space direction="vertical" size={0}>
                <Typography.Text strong>{text ?? '—'}</Typography.Text>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  关联变更 #{row.change_id} · {row.analyst_name}
                </Typography.Text>
              </Space>
            ),
          },
          {
            title: '风险等级',
            dataIndex: 'risk_level',
            width: 100,
            render: (v: string) => <Tag color={SEVERITY_COLORS[v]}>{v === 'high' ? '高风险' : v === 'medium' ? '中风险' : '低风险'}</Tag>,
          },
          {
            title: '受影响团队',
            dataIndex: 'affected_teams',
            width: 220,
            render: (teams: string[]) => teams.map((t) => <Tag key={t}>{t}</Tag>),
          },
          {
            title: '行动项',
            dataIndex: 'action_items',
            width: 80,
            render: (items: string[]) => `${items.length} 项`,
          },
          {
            title: '状态',
            dataIndex: 'status',
            width: 100,
            render: (v: string) => <Tag color={v === 'published' ? 'green' : 'default'}>{v === 'published' ? '已发布' : '草稿'}</Tag>,
          },
          {
            title: '更新时间',
            dataIndex: 'updated_at',
            width: 160,
            render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm'),
          },
          {
            title: '操作',
            width: 120,
            render: (_: unknown, row: ImpactAssessment) =>
              row.status === 'draft' ? (
                <Button size="small" type="primary" ghost icon={<SendOutlined />} onClick={() => publishExisting(row)}>
                  发布
                </Button>
              ) : (
                <Typography.Text type="secondary">已通知</Typography.Text>
              ),
          },
        ]}
      />

      <Drawer
        title="新建影响研判"
        open={drawerOpen}
        width={640}
        onClose={() => setDrawerOpen(false)}
        extra={
          <Space>
            <Button onClick={() => submit(false)}>保存草稿</Button>
            <Button type="primary" onClick={() => submit(true)}>
              保存并发布
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical" initialValues={{ risk_level: 'medium', affected_teams: [], action_items: [''] }}>
          <Form.Item name="change_id" label="关联变更（仅可选择已确认/需跟踪的变更）" rules={[{ required: true, message: '请选择变更' }]}>
            <Select
              showSearch
              placeholder={eligibleChanges.length ? '选择需要研判的变更' : '暂无符合条件的变更（待复核/误报不可选）'}
              optionFilterProp="label"
              onChange={onSelectChange}
              options={eligibleChanges.map((c) => ({
                value: c.id,
                label: `#${c.id} [${CHANGE_TYPE_LABELS[c.change_type] ?? c.change_type}] ${c.title}（已确认）`,
              }))}
            />
          </Form.Item>
          <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginTop: -8 }}>
            规则：只有复核结论为「确认变更属实」或「确认，需持续跟踪」的变更才能创建、保存或发布影响研判；待复核与误报变更已被拦截。
          </Typography.Paragraph>
          <Form.Item name="regulation_id" hidden>
            <Input />
          </Form.Item>
          <Form.Item name="risk_level" label="风险等级" rules={[{ required: true }]}>
            <Radio.Group>
              <Radio.Button value="high">高</Radio.Button>
              <Radio.Button value="medium">中</Radio.Button>
              <Radio.Button value="low">低</Radio.Button>
            </Radio.Group>
          </Form.Item>
          <Form.Item name="affected_teams" label="受影响团队 / 部门">
            <Select mode="tags" placeholder="输入团队名称后回车，如：数据治理部、零售业务部" tokenSeparators={[',', '，']} />
          </Form.Item>
          <Form.Item name="affected_business" label="受影响业务条线">
            <Input.TextArea rows={2} placeholder="如：个人金融信息处理、数据出境合作、第三方数据处理…" />
          </Form.Item>
          <Form.Item name="impact_summary" label="影响研判结论">
            <Input.TextArea rows={4} placeholder="说明变化要点、合规差距与业务影响，例如：新增季度报告义务，需在15个工作日内报送三类台账…" />
          </Form.Item>
          <Form.Item label="行动项（整改 / 跟进）">
            <Form.List name="action_items">
              {(fields, { add, remove }) => (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {fields.map((field) => (
                    <Space key={field.key} style={{ width: '100%' }} align="baseline">
                      <Form.Item {...field} rules={[{ required: true, message: '请输入行动项或删除该行' }]} style={{ width: 520, marginBottom: 8 }}>
                        <Input placeholder="如：更新数据合规管理制度并完成评审" />
                      </Form.Item>
                      <Button danger icon={<DeleteOutlined />} onClick={() => remove(field.name)} />
                    </Space>
                  ))}
                  <Button type="dashed" icon={<PlusOutlined />} onClick={() => add()} block>
                    添加行动项
                  </Button>
                </Space>
              )}
            </Form.List>
          </Form.Item>
        </Form>
      </Drawer>
    </Card>
  )
}
