import { useEffect, useState } from 'react'
import {
  App as AntdApp,
  Button,
  Card,
  Form,
  Input,
  Modal,
  Radio,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd'
import { CheckOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { api } from '../api/client'
import type { ReviewTask } from '../types'
import {
  CHANGE_TYPE_LABELS,
  REVIEW_STATUS_LABELS,
  SEVERITY_COLORS,
  SEVERITY_LABELS,
} from '../constants'

const DECISION_LABELS: Record<string, { label: string; color: string }> = {
  confirm: { label: '确认变更属实', color: 'green' },
  need_followup: { label: '确认，需持续跟踪', color: 'orange' },
  false_positive: { label: '误报/无需处理', color: 'default' },
}

export default function ReviewPage() {
  const [tasks, setTasks] = useState<ReviewTask[]>([])
  const [loading, setLoading] = useState(false)
  const [tab, setTab] = useState('pending')
  const [decideTarget, setDecideTarget] = useState<ReviewTask | null>(null)
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()

  const load = async (status: string) => {
    setLoading(true)
    try {
      const resp = await api.get('/api/review/tasks', {
        params: { status_filter: status === 'all' ? 'all' : status === 'pending' ? 'pending' : 'all' },
      })
      let list: ReviewTask[] = resp.data
      if (status === 'pending') {
        list = list.filter((t) => t.status === 'pending' || t.status === 'claimed')
      } else if (status === 'done') {
        list = list.filter((t) => t.status === 'approved' || t.status === 'dismissed')
      }
      setTasks(list)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load(tab)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab])

  const claim = async (task: ReviewTask) => {
    await api.post(`/api/review/tasks/${task.id}/claim`)
    message.success('已认领，请尽快出具复核结论')
    load(tab)
  }

  const submitDecision = async () => {
    const values = await form.validateFields()
    if (!decideTarget) return
    await api.post(`/api/review/tasks/${decideTarget.id}/decide`, values)
    message.success('复核结论已提交，订阅人将收到通知')
    setDecideTarget(null)
    form.resetFields()
    load(tab)
  }

  const columns = [
    { title: '任务ID', dataIndex: 'id', width: 80 },
    {
      title: '变更法规',
      dataIndex: 'change_title',
      render: (text: string, row: ReviewTask) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{text}</Typography.Text>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {row.source_name} · {row.summary}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'change_type',
      width: 110,
      render: (v: string) => <Tag color="blue">{CHANGE_TYPE_LABELS[v] ?? v}</Tag>,
    },
    {
      title: '严重度',
      dataIndex: 'severity',
      width: 80,
      render: (v: string) => <Tag color={SEVERITY_COLORS[v]}>{SEVERITY_LABELS[v]}</Tag>,
    },
    {
      title: '任务状态',
      dataIndex: 'status',
      width: 100,
      render: (v: string) => <Tag color={v === 'pending' ? 'orange' : v === 'claimed' ? 'blue' : 'default'}>{REVIEW_STATUS_LABELS[v] ?? v}</Tag>,
    },
    {
      title: '处理人',
      dataIndex: 'assignee_name',
      width: 110,
      render: (v: string | null) => v ?? <Typography.Text type="secondary">未认领</Typography.Text>,
    },
    {
      title: '结论',
      dataIndex: 'decision',
      width: 150,
      render: (v: string, row: ReviewTask) =>
        v ? (
          <Space direction="vertical" size={0}>
            <Tag color={DECISION_LABELS[v]?.color}>{DECISION_LABELS[v]?.label ?? v}</Tag>
            {row.comment && (
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                {row.comment}
              </Typography.Text>
            )}
          </Space>
        ) : (
          '-'
        ),
    },
    {
      title: '发现时间',
      dataIndex: 'detected_at',
      width: 150,
      render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      width: 180,
      render: (_: unknown, row: ReviewTask) =>
        row.status === 'pending' || row.status === 'claimed' ? (
          <Space>
            {row.status === 'pending' && (
              <Button size="small" onClick={() => claim(row)}>
                认领
              </Button>
            )}
            <Button size="small" type="primary" icon={<CheckOutlined />} onClick={() => setDecideTarget(row)}>
              出具结论
            </Button>
          </Space>
        ) : (
          <Typography.Text type="secondary">
            {dayjs(row.decided_at).format('MM-DD HH:mm')} 已完成
          </Typography.Text>
        ),
    },
  ]

  return (
    <Card
      title="人工复核队列"
      extra={
        <Button icon={<ReloadOutlined />} onClick={() => load(tab)}>
          刷新
        </Button>
      }
    >
      <Typography.Paragraph type="secondary">
        系统识别的所有变更先进入复核队列，由分析师确认是否为真实监管变化、是否需要跟踪；确认后可发起影响研判并向业务团队说明结论来源（快照与采集运行均可追溯）。
      </Typography.Paragraph>
      <Tabs
        activeKey={tab}
        onChange={setTab}
        items={[
          { key: 'pending', label: '待处理' },
          { key: 'done', label: '已处理' },
        ]}
      />
      <Table rowKey="id" loading={loading} dataSource={tasks} columns={columns} pagination={{ pageSize: 15 }} />

      <Modal
        title="出具复核结论"
        open={!!decideTarget}
        onOk={submitDecision}
        onCancel={() => setDecideTarget(null)}
        okText="提交结论"
        cancelText="取消"
      >
        {decideTarget && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Typography.Text strong>{decideTarget.change_title}</Typography.Text>
            <Typography.Text type="secondary">{decideTarget.summary}</Typography.Text>
            <Form form={form} layout="vertical" initialValues={{ decision: 'confirm', comment: '' }}>
              <Form.Item name="decision" label="复核结论" rules={[{ required: true }]}>
                <Radio.Group>
                  <Space direction="vertical">
                    <Radio value="confirm">确认变更属实 —— 变化需要处理，进入研判</Radio>
                    <Radio value="need_followup">确认变更，需持续跟踪 —— 影响尚不明确</Radio>
                    <Radio value="false_positive">误报/无需处理 —— 排版调整、转载差异等</Radio>
                  </Space>
                </Radio.Group>
              </Form.Item>
              <Form.Item name="comment" label="复核意见（将同步给订阅通知接收人）">
                <Input.TextArea rows={4} placeholder="说明判断依据，例如：新增第十五条季度报告义务，附件检查要点同步更新…" />
              </Form.Item>
            </Form>
          </Space>
        )}
      </Modal>
    </Card>
  )
}
