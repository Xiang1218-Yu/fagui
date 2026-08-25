import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Table, Card, Input, Select, Tag, Space, Button, Statistic, Row, Col } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import { changesApi } from '../api';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';

const { Option } = Select;

const changeTypeLabels: Record<string, string> = {
  new: '新增法规',
  content_update: '内容更新',
  attachment_update: '附件更新',
  status_change: '状态变更',
  repeal: '废止',
};

export default function Changes() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [keyword, setKeyword] = useState('');
  const [severity, setSeverity] = useState<string>();
  const [changeType, setChangeType] = useState<string>();
  const [isReviewed, setIsReviewed] = useState<boolean>();

  const { data, isLoading } = useQuery({
    queryKey: ['changes', page, pageSize, keyword, severity, changeType, isReviewed],
    queryFn: () => changesApi.list({
      page, page_size: pageSize,
      keyword: keyword || undefined,
      severity,
      change_type: changeType,
      is_reviewed: isReviewed,
    }),
    refetchInterval: 10000,
  });

  const pendingCount = data?.items?.filter(c => !c.is_reviewed).length || 0;

  const columns = [
    {
      title: '变更标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (text: string, record: { id: string }) => (
        <a onClick={() => navigate(`/changes/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '法规',
      dataIndex: 'regulation_title',
      key: 'regulation_title',
      ellipsis: true,
      width: 200,
    },
    {
      title: '来源',
      dataIndex: 'source_name',
      key: 'source_name',
      width: 120,
      ellipsis: true,
    },
    {
      title: '类型',
      dataIndex: 'change_type',
      key: 'change_type',
      width: 100,
      render: (t: string) => <Tag>{changeTypeLabels[t] || t}</Tag>,
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      width: 90,
      render: (s: string) => (
        <span className={`severity-${s}`}>
          {s === 'critical' ? '严重' : s === 'high' ? '高' : s === 'medium' ? '中' : '低'}
        </span>
      ),
    },
    {
      title: '复核状态',
      dataIndex: 'review_status',
      key: 'review_status',
      width: 100,
      render: (status: string) => {
        if (!status) return <Tag>待处理</Tag>;
        const labels: Record<string, { color: string; text: string }> = {
          pending: { color: 'orange', text: '待复核' },
          in_review: { color: 'blue', text: '复核中' },
          confirmed: { color: 'green', text: '已确认' },
          dismissed: { color: 'default', text: '已忽略' },
          escalated: { color: 'red', text: '已升级' },
        };
        const cfg = labels[status] || { color: 'default', text: status };
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '变更量',
      key: 'stats',
      width: 120,
      render: (_: unknown, r: { diff_stats?: { lines_added?: number; lines_removed?: number } }) => (
        <Space size="small">
          {r.diff_stats?.lines_added ? <span style={{ color: '#52c41a' }}>+{r.diff_stats.lines_added}</span> : null}
          {r.diff_stats?.lines_removed ? <span style={{ color: '#ff4d4f' }}>-{r.diff_stats.lines_removed}</span> : null}
        </Space>
      ),
    },
    {
      title: '检测时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (d: string) => dayjs(d).format('YYYY-MM-DD HH:mm'),
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>变更对比</h2>
        <p>查看系统检测到的法规内容变化和附件更新</p>
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title="总变更数" value={data?.total || 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="待复核" value={pendingCount} valueStyle={{ color: '#faad14' }} />
          </Card>
        </Col>
      </Row>

      <Card>
        <div className="filter-bar">
          <Input
            placeholder="搜索变更标题或法规"
            prefix={<SearchOutlined />}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            style={{ width: 280 }}
            allowClear
          />
          <Select placeholder="严重程度" allowClear style={{ width: 120 }} value={severity} onChange={setSeverity}>
            <Option value="critical">严重</Option>
            <Option value="high">高</Option>
            <Option value="medium">中</Option>
            <Option value="low">低</Option>
          </Select>
          <Select placeholder="变更类型" allowClear style={{ width: 130 }} value={changeType} onChange={setChangeType}>
            {Object.entries(changeTypeLabels).map(([k, v]) => (
              <Option key={k} value={k}>{v}</Option>
            ))}
          </Select>
          <Select placeholder="复核状态" allowClear style={{ width: 120 }} value={isReviewed} onChange={setIsReviewed}>
            <Option value={false}>未复核</Option>
            <Option value={true}>已复核</Option>
          </Select>
          <Button icon={<ReloadOutlined />} onClick={() => {
            setKeyword(''); setSeverity(undefined); setChangeType(undefined); setIsReviewed(undefined);
          }}>
            重置
          </Button>
        </div>

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
