import { useEffect, useState } from 'react'
import {
  Button,
  Card,
  Descriptions,
  Drawer,
  Empty,
  Input,
  Modal,
  Space,
  Table,
  Tag,
  Timeline,
  Typography,
} from 'antd'
import { DownloadOutlined, FileTextOutlined, PaperClipOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { api, downloadSnapshot } from '../api/client'
import type { DocItem, Regulation, Snapshot } from '../types'

export default function RegulationsPage() {
  const [keyword, setKeyword] = useState('')
  const [regs, setRegs] = useState<Regulation[]>([])
  const [loading, setLoading] = useState(false)
  const [detail, setDetail] = useState<{ regulation: Regulation; documents: DocItem[]; source_count: number } | null>(null)
  const [snapshotsMap, setSnapshotsMap] = useState<Record<number, Snapshot[]>>({})
  const [snapshotText, setSnapshotText] = useState<{ title: string; text: string } | null>(null)

  const load = async (kw = '') => {
    setLoading(true)
    try {
      const resp = await api.get('/api/regulations', { params: kw ? { keyword: kw } : {} })
      setRegs(resp.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const openDetail = async (reg: Regulation) => {
    const resp = await api.get(`/api/regulations/${reg.id}`)
    setDetail(resp.data)
    setSnapshotsMap({})
  }

  const viewSnapshots = async (doc: DocItem) => {
    const resp = await api.get(`/api/documents/${doc.id}/snapshots`)
    setSnapshotsMap((prev) => ({ ...prev, [doc.id]: resp.data }))
  }

  const viewText = async (snap: Snapshot) => {
    const text = await downloadSnapshot(snap.id, 'text')
    setSnapshotText({ title: `快照 #${snap.id} 抽取文本`, text })
  }

  return (
    <Card
      title="法规库（多来源自动归并）"
      extra={
        <Space>
          <Input
            prefix={<SearchOutlined />}
            placeholder="搜索标题 / 文号"
            allowClear
            style={{ width: 260 }}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onPressEnter={() => load(keyword)}
          />
          <Button icon={<ReloadOutlined />} onClick={() => load(keyword)}>
            刷新
          </Button>
        </Space>
      }
    >
      <Typography.Paragraph type="secondary">
        系统按文号（如「京金规〔2026〕3号」）与标题相似度自动归并同一法规在不同来源的转载页面；每次采集均留存不可变快照，支持原文比对与原始文件下载，结论全程可追溯。
      </Typography.Paragraph>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={regs}
        pagination={{ pageSize: 15 }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          {
            title: '法规标题',
            dataIndex: 'title',
            render: (text: string, row: Regulation) => (
              <a onClick={() => openDetail(row)}>{text}</a>
            ),
          },
          {
            title: '文号',
            dataIndex: 'reg_number',
            width: 160,
            render: (v: string | null) => (v ? <Tag color="blue">{v}</Tag> : <Typography.Text type="secondary">未识别</Typography.Text>),
          },
          { title: '发布机构', dataIndex: 'authority', width: 220, ellipsis: true },
          {
            title: '状态',
            dataIndex: 'status',
            width: 90,
            render: (v: string) => <Tag color={v === 'active' ? 'green' : 'default'}>{v === 'active' ? '现行有效' : v}</Tag>,
          },
          {
            title: '更新时间',
            dataIndex: 'updated_at',
            width: 160,
            render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm'),
          },
        ]}
      />

      <Drawer
        title="法规详情与采集来源"
        open={!!detail}
        width={860}
        onClose={() => setDetail(null)}
      >
        {detail && (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="标题">{detail.regulation.title}</Descriptions.Item>
              <Descriptions.Item label="文号">{detail.regulation.reg_number || '未识别'}</Descriptions.Item>
              <Descriptions.Item label="发布机构">{detail.regulation.authority}</Descriptions.Item>
              <Descriptions.Item label="采集来源数（转载归并）">
                <Tag color="purple">{detail.source_count} 个来源</Tag>
              </Descriptions.Item>
            </Descriptions>

            <Typography.Text strong>关联页面与附件（{detail.documents.length}）</Typography.Text>
            <Table
              rowKey="id"
              size="small"
              pagination={false}
              dataSource={detail.documents}
              expandable={{
                rowExpandable: () => true,
                expandedRowRender: (doc: DocItem) => {
                  const docSnaps = snapshotsMap[doc.id]
                  if (!docSnaps) {
                    return (
                      <Button size="small" type="link" onClick={() => viewSnapshots(doc)}>
                        加载该文档的快照时间线（{doc.snapshot_count} 个快照）
                      </Button>
                    )
                  }
                  const latestId = Math.max(...docSnaps.map((s) => s.id))
                  return (
                    <Timeline
                      items={docSnaps.map((s) => ({
                        color: s.id === latestId ? 'green' : 'gray',
                        children: (
                          <Space direction="vertical" size={2}>
                            <Space>
                              <Typography.Text strong>快照 #{s.id}</Typography.Text>
                              <Tag>运行 #{s.crawl_run_id}</Tag>
                              <Typography.Text type="secondary">
                                {dayjs(s.fetched_at).format('YYYY-MM-DD HH:mm:ss')}
                              </Typography.Text>
                            </Space>
                            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                              {s.size_bytes} 字节 · 文本哈希 {s.text_hash.slice(0, 12)}…
                            </Typography.Text>
                            <Space>
                              <Button size="small" icon={<FileTextOutlined />} onClick={() => viewText(s)}>
                                查看抽取文本
                              </Button>
                              <Button size="small" icon={<DownloadOutlined />} onClick={() => downloadSnapshot(s.id, 'raw')}>
                                下载原始文件
                              </Button>
                            </Space>
                          </Space>
                        ),
                      }))}
                    />
                  )
                },
              }}
              columns={[
                {
                  title: '类型',
                  dataIndex: 'doc_type',
                  width: 90,
                  render: (v: string) =>
                    v === 'attachment' ? <Tag icon={<PaperClipOutlined />} color="orange">附件</Tag> : <Tag color="blue">页面</Tag>,
                },
                {
                  title: '标题',
                  dataIndex: 'title',
                  render: (text: string, row: DocItem) => (
                    <Space direction="vertical" size={0}>
                      <Typography.Text>{row.attachment_name || text}</Typography.Text>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        {row.url}
                      </Typography.Text>
                    </Space>
                  ),
                },
                { title: '来源', dataIndex: 'source_name', width: 180, ellipsis: true },
                { title: '快照数', dataIndex: 'snapshot_count', width: 80 },
                {
                  title: '最近采集',
                  dataIndex: 'last_seen_at',
                  width: 150,
                  render: (v: string) => dayjs(v).format('MM-DD HH:mm'),
                },
              ]}
            />
          </Space>
        )}
      </Drawer>

      <Modal
        title={snapshotText?.title}
        open={!!snapshotText}
        onCancel={() => setSnapshotText(null)}
        footer={null}
        width={760}
      >
        {snapshotText?.text ? <div className="snapshot-text">{snapshotText.text}</div> : <Empty description="无文本内容" />}
      </Modal>
    </Card>
  )
}
