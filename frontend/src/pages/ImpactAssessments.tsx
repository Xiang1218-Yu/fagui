import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Table, Card, Tag, Space, Button, Select, Input, Row, Col, Statistic } from 'antd';
import { ReloadOutlined, SearchOutlined, AlertOutlined } from '@ant-design/icons';
import { impactApi } from '../api';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';

const { Option } = Select;

const levelConfig: Record<string, { color: string; label: string }> = {
  none: { color: 'default', label: '无影响' },
  low: { color: 'green', label: '低' },
  medium: { color: 'gold', label: '中' },
  high: { color: 'orange', label: '高' },
  critical: { color: 'red', label: '严重' },
};

const statusLabels: Record<string, string> = {
  draft: '草稿',
  submitted: '已提交',
};

export default function ImpactAssessments() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [level, setLevel] = useState<string>();
  const [keyword, setKeyword] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['impact-assessments', page, pageSize, level, keyword],
    queryFn: () => impactApi.list({
      page, page_size: pageSize,
      overall_level: level,
    }),
  });

  const columns = [
    {
      title: '关联变更',
      dataIndex: 'change_id',
      key: 'change_id',
      width: 100,
      render: (id: string) => id ? <Tag color="blue">变更记录</Tag> : '-',
    },
    {
      title: '影响等级',
      dataIndex: 'overall_level',
      key: 'overall_level',
      width: 100,
      render: (l: string) => (
        <Tag color={levelConfig[l]?.color}>{levelConfig[l]?.label || l}</Tag>
      ),
    },
    {
      title: '受影响团队',
      dataIndex: 'affected_teams',
      key: 'affected_teams',
      width: 200,
      render: (teams: string[]) => teams?.length ? (
        <Space size={[4, 4]} wrap>
          {teams.slice(0, 3).map(t => <Tag key={t}>{t}</Tag>)}
          {teams.length > 3 && <Tag>+{teams.length - 3}</Tag>}
        </Space>
      ) : '-',
    },
    {
      title: '合规领域',
      dataIndex: 'compliance_areas',
      key: 'compliance_areas',
      width: 180,
      render: (areas: string[]) => areas?.length ? (
        <Space size={[4, 4]} wrap>
          {areas.slice(0, 2).map(a => <Tag key={a} color="purple">{a}</Tag>)}
          {areas.length > 2 && <Tag>+{areas.length - 2}</Tag>}
        </Space>
      ) : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (s: string) => <Tag>{statusLabels[s] || s}</Tag>,
    },
    {
      title: '评估人',
      dataIndex: 'assessor_name',
      key: 'assessor_name',
      width: 100,
      render: (n: string) => n || '-',
    },
    {
      title: '截止日期',
      dataIndex: 'deadline',
      key: 'deadline',
      width: 120,
      render: (d: string) => d ? dayjs(d).format('YYYY-MM-DD') : '-',
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 160,
      render: (d: string) => dayjs(d).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: unknown, record: { id: string }) => (
        <Button type="link" size="small" onClick={() => navigate(`/impact/${record.id}`)}>
          查看
        </Button>
      ),
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>影响研判</h2>
        <p>评估法规变更对业务、系统和合规的影响</p>
      </div>

      <Card>
        <div className="filter-bar">
          <Input
            placeholder="搜索分析内容"
            prefix={<SearchOutlined />}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            style={{ width: 260 }}
            allowClear
          />
          <Select placeholder="影响等级" allowClear style={{ width: 120 }} value={level} onChange={setLevel}>
            {Object.entries(levelConfig).map(([k, v]) => (
              <Option key={k} value={k}>{v.label}</Option>
            ))}
          </Select>
          <Button icon={<ReloadOutlined />} onClick={() => { setKeyword(''); setLevel(undefined); }}>
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
