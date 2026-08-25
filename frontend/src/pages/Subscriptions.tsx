import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Table, Card, Button, Modal, Form, Input, Select, Switch,
  Tag, Space, message, Popconfirm,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined, BellOutlined,
} from '@ant-design/icons';
import { subscriptionsApi } from '../api';
import type { Subscription } from '../types';
import dayjs from 'dayjs';

const { TextArea } = Input;
const { Option } = Select;

const channelLabels: Record<string, string> = {
  email: '邮件',
  in_app: '站内信',
  webhook: 'Webhook',
};

export default function Subscriptions() {
  const queryClient = useQueryClient();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingSub, setEditingSub] = useState<Subscription | null>(null);
  const [form] = Form.useForm();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const { data, isLoading } = useQuery({
    queryKey: ['subscriptions', page, pageSize],
    queryFn: () => subscriptionsApi.list({ page, page_size: pageSize }),
  });

  const createMutation = useMutation({
    mutationFn: subscriptionsApi.create,
    onSuccess: () => {
      message.success('订阅创建成功');
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
      setModalVisible(false);
      form.resetFields();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Subscription> }) =>
      subscriptionsApi.update(id, data),
    onSuccess: () => {
      message.success('订阅已更新');
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
      setModalVisible(false);
      setEditingSub(null);
      form.resetFields();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: subscriptionsApi.delete,
    onSuccess: () => {
      message.success('订阅已删除');
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
    },
  });

  const handleSubmit = () => {
    form.validateFields().then(values => {
      const payload = {
        ...values,
        keywords: values.keywords ? values.keywords.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
        severity_filter: values.severity_filter || [],
        channels: values.channels || ['in_app'],
      };
      if (editingSub) {
        updateMutation.mutate({ id: editingSub.id, data: payload });
      } else {
        createMutation.mutate(payload);
      }
    });
  };

  const openEdit = (sub: Subscription) => {
    setEditingSub(sub);
    form.setFieldsValue({
      ...sub,
      keywords: sub.keywords?.join(', '),
    });
    setModalVisible(true);
  };

  const openCreate = () => {
    setEditingSub(null);
    form.resetFields();
    setModalVisible(true);
  };

  const columns = [
    {
      title: '订阅名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '订阅人',
      key: 'subscriber',
      render: (_: unknown, r: Subscription) => (
        <div>
          <div>{r.user_name || r.user_id}</div>
          {r.user_email && <div style={{ fontSize: 12, color: '#999' }}>{r.user_email}</div>}
        </div>
      ),
    },
    {
      title: '关键词',
      dataIndex: 'keywords',
      key: 'keywords',
      render: (keywords: string[]) => keywords?.length ? (
        <Space size={[4, 4]} wrap>
          {keywords.map(k => <Tag key={k} color="blue">{k}</Tag>)}
        </Space>
      ) : <span style={{ color: '#999' }}>全部</span>,
    },
    {
      title: '严重程度',
      dataIndex: 'severity_filter',
      key: 'severity_filter',
      render: (levels: string[]) => levels?.length ? (
        <Space size={[4, 4]} wrap>
          {levels.map(l => (
            <Tag key={l} className={`severity-${l}`}>
              {l === 'critical' ? '严重' : l === 'high' ? '高' : l === 'medium' ? '中' : '低'}
            </Tag>
          ))}
        </Space>
      ) : <span style={{ color: '#999' }}>全部</span>,
    },
    {
      title: '通知渠道',
      dataIndex: 'channels',
      key: 'channels',
      render: (channels: string[]) => (
        <Space size={[4, 4]} wrap>
          {channels.map(c => <Tag key={c}>{channelLabels[c] || c}</Tag>)}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'default'}>{active ? '启用' : '停用'}</Tag>
      ),
    },
    {
      title: '最近通知',
      dataIndex: 'last_notified_at',
      key: 'last_notified_at',
      width: 160,
      render: (d: string) => d ? dayjs(d).format('YYYY-MM-DD HH:mm') : '从未',
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: Subscription) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除此订阅？" onConfirm={() => deleteMutation.mutate(record.id)}>
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
        <h2>订阅通知</h2>
        <p>设置关键词和过滤条件，自动接收法规变更通知</p>
      </div>

      <Card
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => queryClient.invalidateQueries({ queryKey: ['subscriptions'] })}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              新增订阅
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
        title={editingSub ? '编辑订阅' : '新增订阅'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => { setModalVisible(false); setEditingSub(null); }}
        width={560}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="订阅名称" rules={[{ required: true, message: '请输入订阅名称' }]}>
            <Input placeholder="例如：数据安全相关法规" />
          </Form.Item>
          <Form.Item name="user_id" label="订阅人 ID" rules={[{ required: true }]} initialValue="analyst@compliance">
            <Input />
          </Form.Item>
          <Form.Item name="user_name" label="订阅人姓名">
            <Input />
          </Form.Item>
          <Form.Item name="user_email" label="邮箱地址">
            <Input placeholder="用于接收邮件通知" />
          </Form.Item>
          <Form.Item name="keywords" label="关键词（逗号分隔）">
            <TextArea rows={2} placeholder="数据安全, 个人信息, 反垄断" />
          </Form.Item>
          <Form.Item name="severity_filter" label="严重程度过滤">
            <Select mode="multiple" placeholder="不选则接收所有级别">
              <Option value="critical">严重</Option>
              <Option value="high">高</Option>
              <Option value="medium">中</Option>
              <Option value="low">低</Option>
            </Select>
          </Form.Item>
          <Form.Item name="channels" label="通知渠道" initialValue={['in_app']}>
            <Select mode="multiple">
              <Option value="in_app">站内信</Option>
              <Option value="email">邮件</Option>
              <Option value="webhook">Webhook</Option>
            </Select>
          </Form.Item>
          <Form.Item name="is_active" label="启用订阅" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
