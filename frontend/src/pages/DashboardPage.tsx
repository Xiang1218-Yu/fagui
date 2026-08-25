import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Col, Row, Statistic, Table, Tag, Typography, Button, Space } from 'antd'
import {
  BellOutlined,
  CheckSquareOutlined,
  CloudSyncOutlined,
  FileSearchOutlined,
  GlobalOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { api } from '../api/client'
import type { DashboardStats } from '../types'
import {
  CHANGE_STATUS_COLORS,
  CHANGE_TYPE_LABELS,
  RUN_STATUS_COLORS,
  SEVERITY_COLORS,
} from '../constants'

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const navigate = useNavigate()

  const load = async () => {
    const resp = await api.get('/api/dashboard/stats')
    setStats(resp.data)
  }

  useEffect(() => {
    load()
  }, [])

  const cards = stats?.cards
  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic title="采集来源（启用）" value={cards?.sources_enabled ?? 0} prefix={<GlobalOutlined />} suffix={`/ ${cards?.sources_total ?? 0}`} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="归并法规总数" value={cards?.regulations_total ?? 0} prefix={<FileSearchOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="待复核变更"
              value={cards?.changes_pending ?? 0}
              prefix={<SafetyCertificateOutlined />}
              valueStyle={{ color: (cards?.changes_pending ?? 0) > 0 ? '#cf1322' : undefined }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="复核队列任务" value={cards?.review_pending ?? 0} prefix={<CheckSquareOutlined />} />
          </Card>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic title="24小时采集运行" value={cards?.runs_24h ?? 0} prefix={<CloudSyncOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="未读通知" value={cards?.unread_notifications ?? 0} prefix={<BellOutlined />} />
          </Card>
        </Col>
        <Col span={12}>
          <Card>
            <Space>
              <ThunderboltOutlined />
              <Typography.Text strong>闭环演练：</Typography.Text>
              <Typography.Text type="secondary">
                来源管理 → 立即采集 → 模拟法规修订 → 再次采集 → 变更对比 → 复核队列 → 影响研判 → 订阅通知
              </Typography.Text>
            </Space>
            <Space style={{ marginTop: 12 }}>
              <Button type="primary" onClick={() => navigate('/sources')}>
                前往来源管理
              </Button>
              <Button onClick={() => navigate('/review')}>前往复核队列</Button>
            </Space>
          </Card>
        </Col>
      </Row>

      <Card title="最新变更" extra={<Button type="link" onClick={() => navigate('/changes')}>全部变更</Button>}>
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={stats?.recent_changes ?? []}
          columns={[
            {
              title: '法规',
              dataIndex: 'title',
              ellipsis: true,
              render: (text: string, row) => (
                <a onClick={() => navigate('/changes')}>
                  <Tag color={CHANGE_TYPE_LABELS[row.change_type] ? 'blue' : 'default'}>
                    {CHANGE_TYPE_LABELS[row.change_type] ?? row.change_type}
                  </Tag>
                  {text}
                </a>
              ),
            },
            { title: '来源', dataIndex: 'source_name', width: 200, ellipsis: true },
            {
              title: '严重度',
              dataIndex: 'severity',
              width: 90,
              render: (v: string) => <Tag color={SEVERITY_COLORS[v]}>{v === 'high' ? '高' : v === 'medium' ? '中' : '低'}</Tag>,
            },
            {
              title: '状态',
              dataIndex: 'status',
              width: 100,
              render: (v: string) => <Tag color={CHANGE_STATUS_COLORS[v]}>{v === 'pending_review' ? '待复核' : v === 'confirmed' ? '已确认' : '已驳回'}</Tag>,
            },
            {
              title: '发现时间',
              dataIndex: 'detected_at',
              width: 170,
              render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm'),
            },
          ]}
        />
      </Card>

      <Card title="最新采集运行" extra={<Button type="link" onClick={() => navigate('/runs')}>全部运行</Button>}>
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={stats?.recent_runs ?? []}
          columns={[
            { title: '运行ID', dataIndex: 'id', width: 80 },
            { title: '来源', dataIndex: 'source_name', ellipsis: true },
            {
              title: '状态',
              dataIndex: 'status',
              width: 100,
              render: (v: string) => <Tag color={RUN_STATUS_COLORS[v]}>{v}</Tag>,
            },
            { title: '触发', dataIndex: 'trigger_type', width: 90, render: (v: string) => (v === 'manual' ? '手动' : '调度') },
            { title: '页面', dataIndex: 'pages_fetched', width: 70 },
            { title: '变更', dataIndex: 'changes_detected', width: 70 },
            {
              title: '开始时间',
              dataIndex: 'started_at',
              width: 170,
              render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm'),
            },
          ]}
        />
      </Card>
    </Space>
  )
}
