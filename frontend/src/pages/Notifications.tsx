import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Table, Card, Tag, Space, Button, List, Typography, Tabs, Badge } from 'antd';
import { ReloadOutlined, CheckOutlined, BellOutlined, MailOutlined, ApiOutlined } from '@ant-design/icons';
import { notificationsApi } from '../api';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';

const { Text, Paragraph } = Typography;

const channelIcons: Record<string, React.ReactNode> = {
  email: <MailOutlined />,
  in_app: <BellOutlined />,
  webhook: <ApiOutlined />,
};

const statusConfig: Record<string, { color: string; label: string }> = {
  pending: { color: 'default', label: '待发送' },
  sent: { color: 'blue', label: '已发送' },
  failed: { color: 'red', label: '失败' },
  read: { color: 'green', label: '已读' },
};

export default function Notifications() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [activeTab, setActiveTab] = useState('all');

  const statusFilter = activeTab === 'all' ? undefined : activeTab;

  const { data, isLoading } = useQuery({
    queryKey: ['notifications', page, pageSize, statusFilter],
    queryFn: () => notificationsApi.list({
      page, page_size: pageSize,
      status: statusFilter,
      user_id: 'analyst@compliance',
    }),
    refetchInterval: 15000,
  });

  const markReadMutation = useMutation({
    mutationFn: notificationsApi.markRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => notificationsApi.markAllRead('analyst@compliance'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  const columns = [
    {
      title: '渠道',
      dataIndex: 'channel',
      key: 'channel',
      width: 80,
      render: (channel: string) => (
        <Space>
          {channelIcons[channel]}
          <span style={{ fontSize: 12 }}>{channel === 'email' ? '邮件' : channel === 'in_app' ? '站内' : 'Hook'}</span>
        </Space>
      ),
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (text: string, record: { id: string; status: string; change_id?: string }) => (
        <Space>
          {record.status !== 'read' && <Badge status="processing" />}
          <a
            onClick={() => {
              if (record.change_id) navigate(`/changes/${record.change_id}`);
              markReadMutation.mutate(record.id);
            }}
            style={{ fontWeight: record.status !== 'read' ? 600 : 400 }}
          >
            {text}
          </a>
        </Space>
      ),
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: string) => (
        <Tag color={statusConfig[status]?.color}>{statusConfig[status]?.label || status}</Tag>
      ),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (d: string) => dayjs(d).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: { id: string; status: string }) => (
        record.status !== 'read' ? (
          <Button
            type="link"
            size="small"
            icon={<CheckOutlined />}
            onClick={() => markReadMutation.mutate(record.id)}
          >
            已读
          </Button>
        ) : null
      ),
    },
  ];

  const unreadCount = data?.items?.filter(n => n.status !== 'read').length || 0;

  const tabItems = [
    { key: 'all', label: `全部 (${data?.total || 0})` },
    { key: 'pending', label: '待发送' },
    { key: 'sent', label: '已发送' },
    { key: 'read', label: '已读' },
    { key: 'failed', label: '失败' },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>消息中心</h2>
        <p>查看法规变更通知，支持多种渠道推送</p>
      </div>

      <Card
        extra={
          <Space>
            <Button
              icon={<CheckOutlined />}
              onClick={() => markAllReadMutation.mutate()}
              disabled={unreadCount === 0}
            >
              全部标为已读
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => queryClient.invalidateQueries({ queryKey: ['notifications'] })}
            >
              刷新
            </Button>
          </Space>
        }
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} style={{ marginBottom: 16 }} />

        <Table
          columns={columns}
          dataSource={data?.items || []}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: page,
            pageSize,
            total: data?.total || 0,
            onChange: (p, ps) => { setPage(p); setPageSize(ps); },
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>
    </div>
  );
}
