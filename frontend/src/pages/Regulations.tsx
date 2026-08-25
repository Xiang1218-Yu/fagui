import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Table, Card, Input, Select, Tag, Space, Button } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import { regulationsApi } from '../api';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';

const { Option } = Select;

export default function Regulations() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [keyword, setKeyword] = useState('');
  const [status, setStatus] = useState<string>();

  const { data, isLoading } = useQuery({
    queryKey: ['regulations', page, pageSize, keyword, status],
    queryFn: () => regulationsApi.list({
      page, page_size: pageSize,
      keyword: keyword || undefined,
      status,
    }),
  });

  const columns = [
    {
      title: '法规标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (text: string, record: { id: string }) => (
        <a onClick={() => navigate(`/regulations/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '文号',
      dataIndex: 'regulation_number',
      key: 'regulation_number',
      width: 160,
      ellipsis: true,
    },
    {
      title: '发布机构',
      dataIndex: 'issuing_authority',
      key: 'issuing_authority',
      width: 160,
      ellipsis: true,
    },
    {
      title: '来源',
      dataIndex: 'source_name',
      key: 'source_name',
      width: 140,
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (s: string) => {
        const labels: Record<string, { color: string; text: string }> = {
          draft: { color: 'default', text: '草稿' },
          published: { color: 'green', text: '已发布' },
          amended: { color: 'blue', text: '已修订' },
          repealed: { color: 'red', text: '已废止' },
          superseded: { color: 'orange', text: '已替代' },
        };
        const cfg = labels[s] || { color: 'default', text: s };
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '发布日期',
      dataIndex: 'publish_date',
      key: 'publish_date',
      width: 120,
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD') : '-',
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 160,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>法规库</h2>
        <p>所有已采集的法规文档，支持跨来源归并查看</p>
      </div>

      <Card>
        <div className="filter-bar">
          <Input
            placeholder="搜索标题、文号或机构"
            prefix={<SearchOutlined />}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            style={{ width: 300 }}
            allowClear
          />
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 140 }}
            value={status}
            onChange={setStatus}
          >
            <Option value="published">已发布</Option>
            <Option value="amended">已修订</Option>
            <Option value="repealed">已废止</Option>
            <Option value="superseded">已替代</Option>
          </Select>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => { setKeyword(''); setStatus(undefined); }}
          >
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
