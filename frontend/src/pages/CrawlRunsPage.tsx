import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Button, Card, Drawer, Select, Space, Table, Tag, Typography } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { api } from '../api/client'
import type { CrawlRun, Source } from '../types'
import { RUN_STATUS_COLORS, RUN_STATUS_LABELS } from '../constants'

export default function CrawlRunsPage() {
  const [runs, setRuns] = useState<CrawlRun[]>([])
  const [sources, setSources] = useState<Source[]>([])
  const [loading, setLoading] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()
  const [detail, setDetail] = useState<CrawlRun | null>(null)
  const sourceFilter = searchParams.get('source') ?? ''
  const statusFilter = searchParams.get('status') ?? ''

  const load = async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (sourceFilter) params.source_id = sourceFilter
      if (statusFilter) params.status_filter = statusFilter
      const [runsResp, sourcesResp] = await Promise.all([
        api.get('/api/crawl-runs', { params }),
        api.get('/api/sources'),
      ])
      setRuns(runsResp.data)
      setSources(sourcesResp.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 15000)
    return () => clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sourceFilter, statusFilter])

  const sourceName = (id: number) => sources.find((s) => s.id === id)?.name ?? `来源#${id}`

  return (
    <Card
      title="采集运行记录"
      extra={
        <Space>
          <Select
            allowClear
            placeholder="按来源筛选"
            style={{ width: 220 }}
            value={sourceFilter ? Number(sourceFilter) : undefined}
            onChange={(v) => {
              const next = new URLSearchParams(searchParams)
              if (v) next.set('source', String(v))
              else next.delete('source')
              setSearchParams(next)
            }}
            options={sources.map((s) => ({ value: s.id, label: s.name }))}
          />
          <Select
            allowClear
            placeholder="按状态筛选"
            style={{ width: 140 }}
            value={statusFilter || undefined}
            onChange={(v) => {
              const next = new URLSearchParams(searchParams)
              if (v) next.set('status', v)
              else next.delete('status')
              setSearchParams(next)
            }}
            options={Object.entries(RUN_STATUS_LABELS).map(([value, label]) => ({ value, label }))}
          />
          <Button icon={<ReloadOutlined />} onClick={load}>
            刷新
          </Button>
        </Space>
      }
    >
      <Table
        rowKey="id"
        loading={loading}
        dataSource={runs}
        pagination={{ pageSize: 15 }}
        columns={[
          { title: '运行ID', dataIndex: 'id', width: 80 },
          {
            title: '来源',
            dataIndex: 'source_id',
            ellipsis: true,
            render: (id: number) => sourceName(id),
          },
          {
            title: '触发方式',
            dataIndex: 'trigger_type',
            width: 100,
            render: (v: string) => <Tag color={v === 'manual' ? 'geekblue' : 'purple'}>{v === 'manual' ? '手动触发' : '定时调度'}</Tag>,
          },
          {
            title: '状态',
            dataIndex: 'status',
            width: 100,
            render: (v: string) => <Tag color={RUN_STATUS_COLORS[v]}>{RUN_STATUS_LABELS[v] ?? v}</Tag>,
          },
          { title: '页面', dataIndex: 'pages_fetched', width: 70 },
          { title: '附件', dataIndex: 'attachments_fetched', width: 70 },
          {
            title: '发现变更',
            dataIndex: 'changes_detected',
            width: 90,
            render: (v: number) => (
              <Typography.Text strong type={v > 0 ? 'danger' : undefined}>
                {v}
              </Typography.Text>
            ),
          },
          { title: '新法规', dataIndex: 'new_regulations', width: 80 },
          {
            title: '开始时间',
            dataIndex: 'started_at',
            width: 160,
            render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm:ss'),
          },
          {
            title: '耗时',
            width: 90,
            render: (_, row) =>
              row.finished_at
                ? `${Math.max(1, dayjs(row.finished_at).diff(dayjs(row.started_at), 'second'))}s`
                : '-',
          },
          {
            title: '操作',
            width: 100,
            render: (_, row) => (
              <Button
                size="small"
                onClick={async () => {
                  const resp = await api.get(`/api/crawl-runs/${row.id}`)
                  setDetail(resp.data)
                }}
              >
                查看日志
              </Button>
            ),
          },
        ]}
      />

      <Drawer
        title={detail ? `采集运行 #${detail.id} 日志` : ''}
        open={!!detail}
        width={760}
        onClose={() => setDetail(null)}
      >
        {detail && (
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Space wrap>
              <Tag color={RUN_STATUS_COLORS[detail.status]}>{RUN_STATUS_LABELS[detail.status]}</Tag>
              <Tag>{sourceName(detail.source_id)}</Tag>
              <Tag>页面 {detail.pages_fetched}</Tag>
              <Tag>附件 {detail.attachments_fetched}</Tag>
              <Tag color={detail.changes_detected ? 'red' : 'default'}>变更 {detail.changes_detected}</Tag>
              <Tag>新法规 {detail.new_regulations}</Tag>
            </Space>
            {detail.error && (
              <Typography.Paragraph type="danger">
                错误：{detail.error}
              </Typography.Paragraph>
            )}
            <div className="run-log">{detail.log || '（无日志）'}</div>
          </Space>
        )}
      </Drawer>
    </Card>
  )
}
