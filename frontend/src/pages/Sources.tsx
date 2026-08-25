import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Table, Button, Modal, Form, Input, Select, InputNumber,
  Switch, Tag, Space, message, Popconfirm, Card,
} from 'antd';
import {
  PlusOutlined, PlayCircleOutlined, PauseCircleOutlined,
  ReloadOutlined, DeleteOutlined, EditOutlined,
} from '@ant-design/icons';
import { sourcesApi } from '../api';
import type { Source } from '../types';
import dayjs from 'dayjs';

const { TextArea } = Input;
const { Option } = Select;

const sourceTypeLabels: Record<string, string> = {
  regulatory: '监管机构',
  association: '行业协会',
  consultation: '公开征求意见',
  other: '其他',
};

const statusConfig: Record<string, { color: string; label: string }> = {
  active: { color: 'green', label: '活跃' },
  paused: { color: 'default', label: '已暂停' },
  error: { color: 'red', label: '错误' },
};

export default function Sources() {
  const queryClient = useQueryClient();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingSource, setEditingSource] = useState<Source | null>(null);
  const [form] = Form.useForm();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const { data, isLoading } = useQuery({
    queryKey: ['sources', page, pageSize],
    queryFn: () => sourcesApi.list({ page, page_size: pageSize }),
  });

  const createMutation = useMutation({
    mutationFn: sourcesApi.create,
    onSuccess: () => {
      message.success('来源创建成功');
      queryClient.invalidateQueries({ queryKey: ['sources'] });
      setModalVisible(false);
      form.resetFields();
    },
    onError: () => message.error('创建失败'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Source> }) =>
      sourcesApi.update(id, data),
    onSuccess: () => {
      message.success('来源更新成功');
      queryClient.invalidateQueries({ queryKey: ['sources'] });
      setModalVisible(false);
      setEditingSource(null);
      form.resetFields();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: sourcesApi.delete,
    onSuccess: () => {
      message.success('来源已删除');
      queryClient.invalidateQueries({ queryKey: ['sources'] });
    },
  });

  const crawlMutation = useMutation({
    mutationFn: sourcesApi.triggerCrawl,
    onSuccess: () => {
      message.success('采集任务已触发');
      queryClient.invalidateQueries({ queryKey: ['sources'] });
      queryClient.invalidateQueries({ queryKey: ['crawl-runs'] });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: sourcesApi.pause,
    onSuccess: () => {
      message.success('来源已暂停');
      queryClient.invalidateQueries({ queryKey: ['sources'] });
    },
  });

  const resumeMutation = useMutation({
    mutationFn: sourcesApi.resume,
    onSuccess: () => {
      message.success('来源已恢复');
      queryClient.invalidateQueries({ queryKey: ['sources'] });
    },
  });

  const handleSubmit = () => {
    form.validateFields().then(values => {
      const payload = {
        ...values,
        allowed_paths: values.allowed_paths ? values.allowed_paths.split('\n').filter(Boolean) : [],
        excluded_paths: values.excluded_paths ? values.excluded_paths.split('\n').filter(Boolean) : [],
      };
      if (editingSource) {
        updateMutation.mutate({ id: editingSource.id, data: payload });
      } else {
        createMutation.mutate(payload);
      }
    });
  };

  const openEdit = (source: Source) => {
    setEditingSource(source);
    form.setFieldsValue({
      ...source,
      allowed_paths: source.allowed_paths?.join('\n'),
      excluded_paths: source.excluded_paths?.join('\n'),
    });
    setModalVisible(true);
  };

  const openCreate = () => {
    setEditingSource(null);
    form.resetFields();
    setModalVisible(true);
  };

  const columns = [
    {
      title: '来源名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Source) => (
        <div>
          <div style={{ fontWeight: 500 }}>{text}</div>
          <a href={record.url} target="_blank" rel="noreferrer" style={{ fontSize: 12, color: '#999' }}>
            {record.url}
          </a>
        </div>
      ),
    },
    {
      title: '类型',
      dataIndex: 'source_type',
      key: 'source_type',
      width: 100,
      render: (type: string) => <Tag>{sourceTypeLabels[type] || type}</Tag>,
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
      title: '采集频率',
      dataIndex: 'crawl_frequency_minutes',
      key: 'crawl_frequency_minutes',
      width: 100,
      render: (mins: number) => {
        if (mins >= 1440) return `${mins / 1440}天`;
        if (mins >= 60) return `${mins / 60}小时`;
        return `${mins}分钟`;
      },
    },
    {
      title: '最近采集',
      dataIndex: 'last_crawled_at',
      key: 'last_crawled_at',
      width: 160,
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '从未',
    },
    {
      title: '操作',
      key: 'actions',
      width: 240,
      render: (_: unknown, record: Source) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<PlayCircleOutlined />}
            loading={crawlMutation.isPending && crawlMutation.variables === record.id}
            onClick={() => crawlMutation.mutate(record.id)}
          >
            采集
          </Button>
          {record.status === 'active' ? (
            <Button type="link" size="small" icon={<PauseCircleOutlined />} onClick={() => pauseMutation.mutate(record.id)}>
              暂停
            </Button>
          ) : (
            <Button type="link" size="small" icon={<ReloadOutlined />} onClick={() => resumeMutation.mutate(record.id)}>
              恢复
            </Button>
          )}
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除此来源？"
            description="删除后相关采集记录也会被移除"
            onConfirm={() => deleteMutation.mutate(record.id)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>来源管理</h2>
        <p>维护允许采集的监管网站、行业协会和公开征求意见页面</p>
      </div>

      <Card
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => queryClient.invalidateQueries({ queryKey: ['sources'] })}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              新增来源
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

      <Modal
        title={editingSource ? '编辑来源' : '新增采集来源'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => { setModalVisible(false); setEditingSource(null); }}
        width={640}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="来源名称" rules={[{ required: true, message: '请输入来源名称' }]}>
            <Input placeholder="例如：中国证监会官网" />
          </Form.Item>
          <Form.Item name="url" label="入口 URL" rules={[{ required: true, message: '请输入 URL' }]}>
            <Input placeholder="https://www.csrc.gov.cn/" />
          </Form.Item>
          <Form.Item name="base_url" label="基础域名" rules={[{ required: true, message: '请输入基础域名' }]}>
            <Input placeholder="https://www.csrc.gov.cn" />
          </Form.Item>
          <Form.Item name="source_type" label="来源类型" initialValue="regulatory">
            <Select>
              <Option value="regulatory">监管机构</Option>
              <Option value="association">行业协会</Option>
              <Option value="consultation">公开征求意见</Option>
              <Option value="other">其他</Option>
            </Select>
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="来源说明" />
          </Form.Item>
          <Form.Item name="crawl_frequency_minutes" label="采集频率（分钟）" initialValue={1440}>
            <InputNumber min={5} max={10080} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="max_depth" label="最大抓取深度" initialValue={2}>
            <InputNumber min={0} max={10} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="allowed_paths" label="允许路径（每行一个）">
            <TextArea rows={2} placeholder="/news/&#10;/policy/" />
          </Form.Item>
          <Form.Item name="excluded_paths" label="排除路径（每行一个）">
            <TextArea rows={2} placeholder="/login&#10;/search" />
          </Form.Item>
          <Space size="large">
            <Form.Item name="robots_txt_enabled" label="遵守 robots.txt" valuePropName="checked" initialValue={true}>
              <Switch />
            </Form.Item>
            <Form.Item name="respect_crawl_delay" label="遵守爬取延迟" valuePropName="checked" initialValue={true}>
              <Switch />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </div>
  );
}
