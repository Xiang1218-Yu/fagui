import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Card, Descriptions, Tag, Button, Tabs, Table, Spin, Typography, Space,
} from 'antd';
import { ArrowLeftOutlined, FileTextOutlined, PaperClipOutlined, DiffOutlined } from '@ant-design/icons';
import { regulationsApi } from '../api';
import dayjs from 'dayjs';

const { Text, Paragraph } = Typography;

export default function RegulationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: regulation, isLoading } = useQuery({
    queryKey: ['regulation', id],
    queryFn: () => regulationsApi.get(id!),
    enabled: !!id,
  });

  const { data: snapshotsData } = useQuery({
    queryKey: ['regulation-snapshots', id],
    queryFn: () => regulationsApi.getSnapshots(id!),
    enabled: !!id,
  });

  const { data: attachmentsData } = useQuery({
    queryKey: ['regulation-attachments', id],
    queryFn: () => regulationsApi.getAttachments(id!),
    enabled: !!id,
  });

  const { data: changesData } = useQuery({
    queryKey: ['regulation-changes', id],
    queryFn: () => regulationsApi.getChanges(id!),
    enabled: !!id,
  });

  if (isLoading || !regulation) {
    return <div className="page-container"><Spin size="large" /></div>;
  }

  const snapshotColumns = [
    {
      title: '快照时间',
      dataIndex: 'captured_at',
      key: 'captured_at',
      render: (d: string) => dayjs(d).format('YYYY-MM-DD HH:mm:ss'),
    },
    { title: 'HTTP 状态', dataIndex: 'http_status', key: 'http_status', width: 100 },
    { title: '字数', dataIndex: 'word_count', key: 'word_count', width: 100 },
    {
      title: '内容哈希',
      dataIndex: 'content_hash',
      key: 'content_hash',
      ellipsis: true,
      render: (h: string) => <Text code copyable>{h?.substring(0, 16)}...</Text>,
    },
  ];

  const attachmentColumns = [
    { title: '文件名', dataIndex: 'filename', key: 'filename', ellipsis: true },
    { title: '类型', dataIndex: 'content_type', key: 'content_type', width: 150, ellipsis: true },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 100,
      render: (size: number) => size ? `${(size / 1024).toFixed(1)} KB` : '-',
    },
    {
      title: '解析状态',
      dataIndex: 'extraction_status',
      key: 'extraction_status',
      width: 100,
      render: (s: string) => <Tag color={s === 'success' ? 'green' : 'orange'}>{s}</Tag>,
    },
    {
      title: '采集时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (d: string) => dayjs(d).format('YYYY-MM-DD HH:mm'),
    },
  ];

  const changeColumns = [
    {
      title: '变更标题',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: { id: string }) => (
        <a onClick={() => navigate(`/changes/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (s: string) => (
        <span className={`severity-${s}`}>
          {s === 'critical' ? '严重' : s === 'high' ? '高' : s === 'medium' ? '中' : '低'}
        </span>
      ),
    },
    { title: '类型', dataIndex: 'change_type', key: 'change_type', width: 100 },
    {
      title: '新增',
      key: 'added',
      width: 80,
      render: (_: unknown, r: { diff_stats?: { lines_added?: number } }) =>
        r.diff_stats?.lines_added ? <Text type="success">+{r.diff_stats.lines_added}</Text> : '-',
    },
    {
      title: '删除',
      key: 'removed',
      width: 80,
      render: (_: unknown, r: { diff_stats?: { lines_removed?: number } }) =>
        r.diff_stats?.lines_removed ? <Text type="danger">-{r.diff_stats.lines_removed}</Text> : '-',
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (d: string) => dayjs(d).format('YYYY-MM-DD HH:mm'),
    },
  ];

  const tabItems = [
    {
      key: 'snapshots',
      label: <span><FileTextOutlined /> 历史快照 ({snapshotsData?.total || 0})</span>,
      children: (
        <Table
          columns={snapshotColumns}
          dataSource={snapshotsData?.items || []}
          rowKey="id"
          pagination={false}
          size="small"
        />
      ),
    },
    {
      key: 'attachments',
      label: <span><PaperClipOutlined /> 附件 ({attachmentsData?.total || 0})</span>,
      children: (
        <Table
          columns={attachmentColumns}
          dataSource={attachmentsData?.items || []}
          rowKey="id"
          pagination={false}
          size="small"
        />
      ),
    },
    {
      key: 'changes',
      label: <span><DiffOutlined /> 变更记录 ({changesData?.total || 0})</span>,
      children: (
        <Table
          columns={changeColumns}
          dataSource={changesData?.items || []}
          rowKey="id"
          pagination={false}
          size="small"
        />
      ),
    },
  ];

  return (
    <div className="page-container">
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/regulations')}>
          返回列表
        </Button>
      </Space>

      <Card>
        <Descriptions title={regulation.title} column={2} bordered size="small">
          <Descriptions.Item label="文号" span={2}>
            {regulation.regulation_number || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="发布机构">
            {regulation.issuing_authority || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="来源">
            {regulation.source_name || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="发布日期">
            {regulation.publish_date ? dayjs(regulation.publish_date).format('YYYY-MM-DD') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="生效日期">
            {regulation.effective_date ? dayjs(regulation.effective_date).format('YYYY-MM-DD') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color="green">{regulation.status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="首次发现">
            {dayjs(regulation.first_seen_at).format('YYYY-MM-DD HH:mm')}
          </Descriptions.Item>
          <Descriptions.Item label="原文链接" span={2}>
            <a href={regulation.url} target="_blank" rel="noreferrer">{regulation.url}</a>
          </Descriptions.Item>
          {regulation.summary && (
            <Descriptions.Item label="摘要" span={2}>
              <Paragraph>{regulation.summary}</Paragraph>
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card style={{ marginTop: 16 }}>
        <Tabs items={tabItems} />
      </Card>
    </div>
  );
}
