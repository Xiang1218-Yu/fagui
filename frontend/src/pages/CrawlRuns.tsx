import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Table, Button, Tag, Space, Card, Drawer, Typography, message, Select } from 'antd';
import { PlayCircleOutlined, ReloadOutlined, EyeOutlined } from '@ant-design/icons';
import { crawlRunsApi, sourcesApi } from '../api';
import dayjs from 'dayjs';

const { Text, Paragraph } = Typography;
const { Option } = Select;

const statusConfig: Record<string, { color: string; label: string }> = {
  pending: { color: 'default', label: '等待中' },
  running: { color: 'processing', label: '运行中' },
  success: { color: 'success', label: '成功' },
  partial: { color: 'warning', label: '部分成功' },
  failed: { color: 'error', label: '失败' },
};

export default function CrawlRuns() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState<string>();
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string>();

  const { data, isLoading } = useQuery({
    queryKey: ['crawl-runs', page, pageSize, statusFilter],
    queryFn: () => crawlRunsApi.list({ page, page_size: pageSize, status: statusFilter }),
    refetchInterval: 5000,
  });

  const { data: detailData } = useQuery({
    queryKey: ['crawl-run-logs', selectedRunId],
    queryFn: () => selectedRunId ? crawlRunsApi.getLogs(selectedRunId) : null,
    enabled: !!selectedRunId && detailVisible,
  });

  const triggerAllMutation = useMutation({
    mutationFn: sourcesApi.triggerAllCrawls,
    onSuccess: (data) => {
      message.success(`已触发 ${data.triggered} 个采集任务`);
      queryClient.invalidateQueries({ queryKey: ['crawl-runs'] });
    },
  });

  const columns = [
    {
      title: '来源',
      dataIndex: 'source_name',
      key: 'source_name',
      render: (name: string) => name || '未知来源',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={statusConfig[status]?.color}>{statusConfig[status]?.label || status}</Tag>
      ),
    },
    {
      title: '触发方式',
      dataIndex: 'triggered_by',
      key: 'triggered_by',
      width: 90,
      render: (t: string) => t === 'scheduled' ? '定时' : t === 'manual' ? '手动' : t,
    },
    {
      title: '抓取页面',
      dataIndex: 'pages_crawled',
      key: 'pages_crawled',
      width: 90,
    },
    {
      title: '失败',
      dataIndex: 'pages_failed',
      key: 'pages_failed',
      width: 70,
      render: (n: number) => n > 0 ? <Text type="danger">{n}</Text> : n,
    },
    {
      title: '附件',
      dataIndex: 'attachments_downloaded',
      key: 'attachments_downloaded',
      width: 70,
    },
    {
      title: '变更',
      dataIndex: 'changes_detected',
      key: 'changes_detected',
      width: 70,
      render: (n: number) => n > 0 ? <Text strong style={{ color: '#fa541c' }}>{n}</Text> : n,
    },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 160,
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '完成时间',
      dataIndex: 'completed_at',
      key: 'completed_at',
      width: 160,
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: unknown, record: { id: string }) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => { setSelectedRunId(record.id); setDetailVisible(true); }}
        >
          日志
        </Button>
      ),
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>采集运行</h2>
        <p>查看采集任务执行状态和日志</p>
      </div>

      <Card
        extra={
          <Space>
            <Select
              placeholder="状态筛选"
              allowClear
              style={{ width: 120 }}
              value={statusFilter}
              onChange={setStatusFilter}
            >
              {Object.entries(statusConfig).map(([key, cfg]) => (
                <Option key={key} value={key}>{cfg.label}</Option>
              ))}
            </Select>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => queryClient.invalidateQueries({ queryKey: ['crawl-runs'] })}
            >
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              loading={triggerAllMutation.isPending}
              onClick={() => triggerAllMutation.mutate()}
            >
              全部采集
            </Button>
          </Space>
        }
      >
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

      <Drawer
        title="采集运行详情"
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
        width={600}
      >
        {detailData && (
          <div>
            <Paragraph>
              <Text strong>状态：</Text>
              <Tag color={statusConfig[detailData.status as string]?.color}>
                {statusConfig[detailData.status as string]?.label}
              </Tag>
            </Paragraph>
            <Paragraph>
              <Text strong>抓取页面：</Text>{detailData.pages_crawled} 个页面
            </Paragraph>
            <Paragraph>
              <Text strong>失败页面：</Text>{detailData.pages_failed} 个
            </Paragraph>
            {detailData.error_message && (
              <Paragraph>
                <Text strong type="danger">错误信息：</Text>
                <br />
                <Text type="danger">{detailData.error_message}</Text>
              </Paragraph>
            )}
            {detailData.logs && detailData.logs.length > 0 && (
              <div>
                <Text strong>错误日志：</Text>
                <div style={{
                  marginTop: 8,
                  background: '#f5f5f5',
                  padding: 12,
                  borderRadius: 4,
                  maxHeight: 400,
                  overflow: 'auto',
                  fontSize: 12,
                  fontFamily: 'monospace',
                }}>
                  {detailData.logs.map((log: string, i: number) => (
                    <div key={i} style={{ marginBottom: 4 }}>{log}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
}
