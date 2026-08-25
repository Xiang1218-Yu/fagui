import { useQuery } from '@tanstack/react-query';
import { Row, Col, Card, Tag, Table, Spin, Statistic } from 'antd';
import {
  GlobalOutlined, FileTextOutlined, AuditOutlined,
  DiffOutlined, CheckCircleOutlined, ClockCircleOutlined,
} from '@ant-design/icons';
import { dashboardApi } from '../api';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';

const severityColors: Record<string, string> = {
  critical: 'red',
  high: 'orange',
  medium: 'gold',
  low: 'green',
};

const statusColors: Record<string, string> = {
  success: 'green',
  running: 'blue',
  pending: 'default',
  partial: 'orange',
  failed: 'red',
};

const changeTypeLabels: Record<string, string> = {
  new: '新增',
  content_update: '内容更新',
  attachment_update: '附件更新',
  status_change: '状态变更',
  repeal: '废止',
};

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardApi.getStats,
    refetchInterval: 30000,
  });

  if (isLoading || !stats) {
    return <div className="page-container"><Spin size="large" /></div>;
  }

  const crawlColumns = [
    {
      title: '来源',
      dataIndex: 'source_name',
      key: 'source_name',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <Tag color={statusColors[status]}>{status}</Tag>,
    },
    {
      title: '抓取页面',
      dataIndex: 'pages_crawled',
      key: 'pages_crawled',
    },
    {
      title: '检测变更',
      dataIndex: 'changes_detected',
      key: 'changes_detected',
    },
    {
      title: '完成时间',
      dataIndex: 'completed_at',
      key: 'completed_at',
      render: (date: string) => date ? dayjs(date).format('MM-DD HH:mm') : '-',
    },
  ];

  const changeColumns = [
    {
      title: '变更标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
    },
    {
      title: '法规',
      dataIndex: 'regulation_title',
      key: 'regulation_title',
      ellipsis: true,
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => (
        <span className={`severity-${severity}`}>
          {severity === 'critical' ? '严重' : severity === 'high' ? '高' : severity === 'medium' ? '中' : '低'}
        </span>
      ),
    },
    {
      title: '类型',
      dataIndex: 'change_type',
      key: 'change_type',
      render: (type: string) => changeTypeLabels[type] || type,
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('MM-DD HH:mm'),
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>仪表盘</h2>
        <p>法规变更情报与影响研判平台总览</p>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="采集来源"
              value={stats.total_sources}
              prefix={<GlobalOutlined />}
              suffix={<span style={{ fontSize: 14, color: '#52c41a' }}>/ {stats.active_sources} 活跃</span>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="法规总数"
              value={stats.total_regulations}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="待复核变更"
              value={stats.pending_reviews}
              prefix={<AuditOutlined />}
              valueStyle={{ color: stats.pending_reviews > 0 ? '#faad14' : '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="本周变更"
              value={stats.changes_this_week}
              prefix={<DiffOutlined />}
              suffix={<span style={{ fontSize: 14, color: '#666' }}>今日 {stats.changes_today}</span>}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="最近采集任务" extra={<a onClick={() => navigate('/crawl-runs')}>查看全部</a>}>
            <Table
              columns={crawlColumns}
              dataSource={stats.recent_crawls}
              rowKey="id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="最近变更" extra={<a onClick={() => navigate('/changes')}>查看全部</a>}>
            <Table
              columns={changeColumns}
              dataSource={stats.recent_changes}
              rowKey="id"
              pagination={false}
              size="small"
              onRow={(record) => ({
                onClick: () => navigate(`/changes/${record.id}`),
                style: { cursor: 'pointer' },
              })}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={8}>
          <Card title="变更严重程度分布">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {Object.entries(stats.severity_breakdown).map(([level, count]) => (
                <div key={level} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className={`severity-${level}`}>
                    {level === 'critical' ? '严重' : level === 'high' ? '高' : level === 'medium' ? '中' : '低'}
                  </span>
                  <Tag color={severityColors[level]}>{count}</Tag>
                </div>
              ))}
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="复核状态分布">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {Object.entries(stats.review_breakdown).map(([status, count]) => (
                <div key={status} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>
                    {status === 'pending' ? '待处理' :
                     status === 'in_review' ? '复核中' :
                     status === 'confirmed' ? '已确认' :
                     status === 'dismissed' ? '已忽略' : '已升级'}
                  </span>
                  <Tag>{count}</Tag>
                </div>
              ))}
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="来源类型分布">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {Object.entries(stats.source_type_breakdown).map(([type, count]) => (
                <div key={type} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>
                    {type === 'regulatory' ? '监管机构' :
                     type === 'association' ? '行业协会' :
                     type === 'consultation' ? '征求意见' : '其他'}
                  </span>
                  <Tag color="blue">{count}</Tag>
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
