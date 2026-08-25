import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert,
  App as AntdApp,
  Button,
  Card,
  Descriptions,
  Drawer,
  Empty,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd'
import {
  CheckSquareOutlined,
  DownloadOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  LinkOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { api, downloadSnapshot } from '../api/client'
import type { Change, ChangeDetail, DiffRow } from '../types'
import {
  CHANGE_STATUS_COLORS,
  CHANGE_STATUS_LABELS,
  CHANGE_TYPE_LABELS,
  SEVERITY_COLORS,
  SEVERITY_LABELS,
} from '../constants'

function DiffTable({ rows }: { rows: DiffRow[] }) {
  if (rows.length === 0) {
    return <Empty description="无正文文本差异（可能为附件或标题变更）" />
  }
  return (
    <table className="diff-table">
      <thead>
        <tr>
          <th className="ln">旧#</th>
          <th style={{ width: '38%' }}>旧版本正文</th>
          <th className="ln">新#</th>
          <th>新版本正文</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} className={`diff-row-${r.type}`}>
            <td className="ln">{r.old_no ?? ''}</td>
            <td className="old-side">{r.old || (r.type === 'insert' ? '' : ' ')}</td>
            <td className="ln">{r.new_no ?? ''}</td>
            <td className="new-side">{r.new || (r.type === 'delete' ? '' : ' ')}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default function ChangesPage() {
  const [changes, setChanges] = useState<Change[]>([])
  const [loading, setLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [typeFilter, setTypeFilter] = useState<string | undefined>()
  const [detail, setDetail] = useState<ChangeDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const navigate = useNavigate()
  const { message } = AntdApp.useApp()

  const load = async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (statusFilter) params.status_filter = statusFilter
      if (typeFilter) params.change_type = typeFilter
      const resp = await api.get('/api/changes', { params })
      setChanges(resp.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, typeFilter])

  const openDetail = async (change: Change) => {
    setDetailLoading(true)
    setDetail(null)
    try {
      const resp = await api.get(`/api/changes/${change.id}`)
      setDetail(resp.data)
    } finally {
      setDetailLoading(false)
    }
  }

  const setSeverity = async (changeId: number, severity: string) => {
    await api.patch(`/api/changes/${changeId}/severity`, { severity })
    const resp = await api.get(`/api/changes/${changeId}`)
    setDetail(resp.data)
    load()
  }

  return (
    <Card
      title="变更对比"
      extra={
        <Space>
          <Select
            allowClear
            placeholder="处理状态"
            style={{ width: 140 }}
            value={statusFilter}
            onChange={setStatusFilter}
            options={Object.entries(CHANGE_STATUS_LABELS).map(([value, label]) => ({ value, label }))}
          />
          <Select
            allowClear
            placeholder="变更类型"
            style={{ width: 150 }}
            value={typeFilter}
            onChange={setTypeFilter}
            options={Object.entries(CHANGE_TYPE_LABELS).map(([value, label]) => ({ value, label }))}
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
        dataSource={changes}
        pagination={{ pageSize: 15 }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          {
            title: '变更法规 / 页面',
            dataIndex: 'title',
            render: (text: string, row: Change) => (
              <a onClick={() => openDetail(row)}>
                <Tag color="blue">{CHANGE_TYPE_LABELS[row.change_type] ?? row.change_type}</Tag>
                {text}
              </a>
            ),
          },
          {
            title: '摘要',
            dataIndex: 'summary',
            width: 260,
            ellipsis: true,
          },
          {
            title: '严重度',
            dataIndex: 'severity',
            width: 90,
            render: (v: string) => <Tag color={SEVERITY_COLORS[v]}>{SEVERITY_LABELS[v]}</Tag>,
          },
          {
            title: '状态',
            dataIndex: 'status',
            width: 100,
            render: (v: string) => <Tag color={CHANGE_STATUS_COLORS[v]}>{CHANGE_STATUS_LABELS[v] ?? v}</Tag>,
          },
          {
            title: '发现时间',
            dataIndex: 'detected_at',
            width: 160,
            render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm'),
          },
        ]}
      />

      <Drawer
        title="变更详情与正文对比"
        width={1080}
        open={!!detail || detailLoading}
        onClose={() => setDetail(null)}
        destroyOnClose
      >
        {detail && (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="法规" span={2}>
                {detail.regulation ? `${detail.regulation.title}${detail.regulation.reg_number ? `（${detail.regulation.reg_number}）` : ''}` : detail.change.title}
              </Descriptions.Item>
              <Descriptions.Item label="来源">{detail.source?.name}</Descriptions.Item>
              <Descriptions.Item label="类型">
                <Tag color="blue">{CHANGE_TYPE_LABELS[detail.change.change_type]}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="页面链接" span={2}>
                <Typography.Link href={detail.document.url} target="_blank">
                  <LinkOutlined /> {detail.document.url}
                </Typography.Link>
              </Descriptions.Item>
              <Descriptions.Item label="变更摘要" span={2}>
                {detail.change.summary}
              </Descriptions.Item>
              <Descriptions.Item label="严重度">
                <Select
                  size="small"
                  style={{ width: 100 }}
                  value={detail.change.severity}
                  onChange={(v) => setSeverity(detail.change.id, v)}
                  options={[
                    { value: 'high', label: '高' },
                    { value: 'medium', label: '中' },
                    { value: 'low', label: '低' },
                  ]}
                />
              </Descriptions.Item>
              <Descriptions.Item label="复核状态">
                <Tag color={CHANGE_STATUS_COLORS[detail.change.status]}>
                  {CHANGE_STATUS_LABELS[detail.change.status]}
                </Tag>
                {detail.review?.decision && (
                  <Typography.Text type="secondary" style={{ marginLeft: 8 }}>
                    结论：{detail.review.decision === 'confirm' ? '确认变更' : detail.review.decision === 'need_followup' ? '确认并跟踪' : '误报'}
                  </Typography.Text>
                )}
              </Descriptions.Item>
            </Descriptions>

            {(() => {
              const att = (detail.change.changed_fields as { attachments?: Record<string, Array<{ name: string; url: string }>> }).attachments
              if (!att || (!att.added?.length && !att.modified?.length && !att.removed?.length)) return null
              return (
                <Alert
                  type="warning"
                  showIcon
                  message="附件变更"
                  description={
                    <Space direction="vertical" size={4}>
                      {att.added?.map((a, i) => (
                        <Typography.Text key={`a${i}`} type="success">
                          ＋ 新增附件：{a.name || a.url}
                        </Typography.Text>
                      ))}
                      {att.modified?.map((a, i) => (
                        <Typography.Text key={`m${i}`} type="warning">
                          ≠ 附件内容更新：{a.name || a.url}（原始文件哈希已变化，可下载新旧快照比对）
                        </Typography.Text>
                      ))}
                      {att.removed?.map((a, i) => (
                        <Typography.Text key={`r${i}`} type="danger">
                          － 附件移除：{a.name || a.url}
                        </Typography.Text>
                      ))}
                    </Space>
                  }
                />
              )
            })()}

            <Card size="small" title="快照追溯（结论来源）">
              <Space wrap>
                {detail.old_snapshot && (
                  <Card.Grid style={{ width: '50%', padding: 12 }}>
                    <Typography.Text strong>旧版本快照 #{detail.old_snapshot.id}</Typography.Text>
                    <br />
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      采集于 {dayjs(detail.old_snapshot.fetched_at).format('YYYY-MM-DD HH:mm:ss')} · 运行 #{detail.old_snapshot.crawl_run_id}
                      <br />
                      {detail.old_snapshot.size_bytes} 字节 · {detail.old_snapshot.content_hash.slice(0, 16)}…
                    </Typography.Text>
                    <br />
                    <Space style={{ marginTop: 8 }}>
                      <Button size="small" icon={<FileTextOutlined />} onClick={() => downloadSnapshot(detail.old_snapshot!.id, 'text')}>
                        文本
                      </Button>
                      <Button size="small" icon={<DownloadOutlined />} onClick={() => downloadSnapshot(detail.old_snapshot!.id, 'raw')}>
                        原始文件
                      </Button>
                    </Space>
                  </Card.Grid>
                )}
                <Card.Grid style={{ width: detail.old_snapshot ? '50%' : '100%', padding: 12 }}>
                  <Typography.Text strong>新版本快照 #{detail.new_snapshot.id}</Typography.Text>
                  <br />
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    采集于 {dayjs(detail.new_snapshot.fetched_at).format('YYYY-MM-DD HH:mm:ss')} · 运行 #{detail.new_snapshot.crawl_run_id}
                    <br />
                    {detail.new_snapshot.size_bytes} 字节 · {detail.new_snapshot.content_hash.slice(0, 16)}…
                  </Typography.Text>
                  <br />
                  <Space style={{ marginTop: 8 }}>
                    <Button size="small" icon={<FileTextOutlined />} onClick={() => downloadSnapshot(detail.new_snapshot.id, 'text')}>
                      文本
                    </Button>
                    <Button size="small" icon={<DownloadOutlined />} onClick={() => downloadSnapshot(detail.new_snapshot.id, 'raw')}>
                      原始文件
                    </Button>
                  </Space>
                </Card.Grid>
              </Space>
            </Card>

            <div>
              <Typography.Title level={5}>正文逐行对比</Typography.Title>
              <DiffTable rows={detail.diff_rows} />
            </div>

            <Space>
              <Button type="primary" icon={<CheckSquareOutlined />} onClick={() => navigate('/review')}>
                前往复核队列
              </Button>
              <Button
                icon={<ExperimentOutlined />}
                disabled={detail.change.status !== 'confirmed'}
                onClick={() => {
                  if (detail.change.status !== 'confirmed') {
                    message.warning(
                      '只有复核结论为「确认变更属实」或「确认，需持续跟踪」的变更才能发起影响研判；待复核/误报变更已被拦截',
                    )
                    return
                  }
                  navigate('/impact', { state: { changeId: detail.change.id } })
                }}
              >
                发起影响研判
              </Button>
            </Space>
          </Space>
        )}
      </Drawer>
    </Card>
  )
}
