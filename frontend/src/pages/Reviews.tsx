import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Table, Card, Tag, Space, Button, Select, Input, message,
  Drawer, Form, Typography, Row, Col, Statistic,
} from 'antd';
import {
  ReloadOutlined, UserOutlined, CheckOutlined,
  CloseOutlined, ArrowUpOutlined,
} from '@ant-design/icons';
import { reviewsApi } from '../api';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;
const { Option } = Select;

const statusConfig: Record<string, { color: string; label: string }> = {
  pending: { color: 'orange', label: '待复核' },
  in_review: { color: 'blue', label: '复核中' },
  confirmed: { color: 'green', label: '已确认' },
  dismissed: { color: 'default', label: '已忽略' },
  escalated: { color: 'red', label: '已升级' },
};

export default function Reviews() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState<string>('pending');
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [selectedReview, setSelectedReview] = useState<{ id: string; change_id?: string } | null>(null);
  const [form] = Form.useForm();

  const { data, isLoading } = useQuery({
    queryKey: ['reviews', page, pageSize, statusFilter],
    queryFn: () => reviewsApi.list({ page, page_size: pageSize, status: statusFilter }),
    refetchInterval: 10000,
  });

  const { data: statsData } = useQuery({
    queryKey: ['review-stats'],
    queryFn: reviewsApi.getStats,
    refetchInterval: 30000,
  });

  const claimMutation = useMutation({
    mutationFn: ({ id, reviewerId, reviewerName }: { id: string; reviewerId: string; reviewerName: string }) =>
      reviewsApi.claim(id, reviewerId, reviewerName),
    onSuccess: () => {
      message.success('已领取复核任务');
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      queryClient.invalidateQueries({ queryKey: ['review-stats'] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      reviewsApi.update(id, data),
    onSuccess: () => {
      message.success('复核已更新');
      setDrawerVisible(false);
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      queryClient.invalidateQueries({ queryKey: ['review-stats'] });
    },
  });

  const openReviewDrawer = (review: { id: string; change_id?: string }) => {
    setSelectedReview(review);
    form.resetFields();
    setDrawerVisible(true);
  };

  const handleSubmitReview = () => {
    form.validateFields().then(values => {
      if (selectedReview) {
        updateMutation.mutate({
          id: selectedReview.id,
          data: {
            status: values.status,
            decision: values.decision,
            notes: values.notes,
            tags: values.tags || [],
          },
        });
      }
    });
  };

  const columns = [
    {
      title: '变更标题',
      key: 'title',
      ellipsis: true,
      render: (_: unknown, record: { change?: { title?: string } }) => record.change?.title || '-',
    },
    {
      title: '法规',
      key: 'regulation',
      ellipsis: true,
      width: 180,
      render: (_: unknown, record: { change?: { regulation_title?: string } }) =>
        record.change?.regulation_title || '-',
    },
    {
      title: '来源',
      key: 'source',
      width: 120,
      ellipsis: true,
      render: (_: unknown, record: { change?: { source_name?: string } }) =>
        record.change?.source_name || '-',
    },
    {
      title: '严重程度',
      key: 'severity',
      width: 90,
      render: (_: unknown, record: { change?: { severity?: string } }) => {
        const s = record.change?.severity;
        return s ? (
          <span className={`severity-${s}`}>
            {s === 'critical' ? '严重' : s === 'high' ? '高' : s === 'medium' ? '中' : '低'}
          </span>
        ) : '-';
      },
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
      title: '复核人',
      dataIndex: 'reviewer_name',
      key: 'reviewer_name',
      width: 100,
      render: (name: string) => name || '-',
    },
    {
      title: '截止日期',
      dataIndex: 'due_at',
      key: 'due_at',
      width: 120,
      render: (date: string) => date ? dayjs(date).format('MM-DD HH:mm') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: { id: string; status: string; change_id?: string }) => (
        <Space>
          {record.status === 'pending' && (
            <Button
              type="link"
              size="small"
              icon={<UserOutlined />}
              onClick={() => claimMutation.mutate({
                id: record.id,
                reviewerId: 'analyst@compliance',
                reviewerName: '合规分析师',
              })}
            >
              领取
            </Button>
          )}
          <Button type="link" size="small" onClick={() => openReviewDrawer(record)}>
            处理
          </Button>
          {record.change_id && (
            <Button type="link" size="small" onClick={() => navigate(`/changes/${record.change_id}`)}>
              查看
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>复核队列</h2>
        <p>人工确认检测到的变更，提交复核结论</p>
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        {Object.entries(statusConfig).map(([key, cfg]) => (
          <Col key={key} span={4}>
            <Card
              size="small"
              hoverable
              onClick={() => setStatusFilter(key)}
              style={{
                borderColor: statusFilter === key ? '#1677ff' : undefined,
                borderWidth: statusFilter === key ? 2 : 1,
              }}
            >
              <Statistic
                title={cfg.label}
                value={statsData?.[key] || 0}
                valueStyle={{ fontSize: 24 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Card
        extra={
          <Space>
            <Select value={statusFilter} onChange={setStatusFilter} style={{ width: 120 }}>
              {Object.entries(statusConfig).map(([key, cfg]) => (
                <Option key={key} value={key}>{cfg.label}</Option>
              ))}
            </Select>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => queryClient.invalidateQueries({ queryKey: ['reviews'] })}
            >
              刷新
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
        title="复核处理"
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        width={520}
        footer={
          <Space style={{ float: 'right' }}>
            <Button onClick={() => setDrawerVisible(false)}>取消</Button>
            <Button
              type="primary"
              onClick={handleSubmitReview}
              loading={updateMutation.isPending}
            >
              提交结论
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item name="status" label="复核结论" rules={[{ required: true }]} initialValue="confirmed">
            <Select>
              <Option value="confirmed">
                <CheckOutlined /> 确认变更（需要跟进）
              </Option>
              <Option value="dismissed">
                <CloseOutlined /> 忽略（格式变化无实质影响）
              </Option>
              <Option value="escalated">
                <ArrowUpOutlined /> 升级处理（重大变化）
              </Option>
            </Select>
          </Form.Item>
          <Form.Item name="decision" label="决定说明">
            <TextArea rows={3} placeholder="说明该变更为何需要确认、忽略或升级" />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <TextArea rows={2} />
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Select mode="tags" placeholder="添加标签便于分类" />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  );
}
