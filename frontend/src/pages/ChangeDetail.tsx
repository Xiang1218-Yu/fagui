import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card, Button, Spin, Tag, Descriptions, Tabs, Typography, Space,
  Modal, Form, Input, Select, message, Divider, Statistic, Row, Col,
} from 'antd';
import {
  ArrowLeftOutlined, CheckOutlined, CloseOutlined,
  AlertOutlined, AuditOutlined,
} from '@ant-design/icons';
import { changesApi, reviewsApi, impactApi } from '../api';
import dayjs from 'dayjs';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

const changeTypeLabels: Record<string, string> = {
  new: '新增法规',
  content_update: '内容更新',
  attachment_update: '附件更新',
  status_change: '状态变更',
  repeal: '废止',
};

export default function ChangeDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [reviewModalVisible, setReviewModalVisible] = useState(false);
  const [impactModalVisible, setImpactModalVisible] = useState(false);
  const [reviewForm] = Form.useForm();
  const [impactForm] = Form.useForm();

  const { data: change, isLoading } = useQuery({
    queryKey: ['change', id],
    queryFn: () => changesApi.get(id!),
    enabled: !!id,
  });

  const { data: diffData, isLoading: diffLoading } = useQuery({
    queryKey: ['change-diff', id],
    queryFn: () => changesApi.getDiff(id!),
    enabled: !!id,
  });

  const markReviewedMutation = useMutation({
    mutationFn: changesApi.markReviewed,
    onSuccess: () => {
      message.success('已标记为已复核');
      queryClient.invalidateQueries({ queryKey: ['change', id] });
    },
  });

  const submitReviewMutation = useMutation({
    mutationFn: (data: { status: string; decision: string; notes: string; tags: string[] }) =>
      reviewsApi.update(id!, data),
    onSuccess: () => {
      message.success('复核已提交');
      setReviewModalVisible(false);
      reviewForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['change', id] });
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
    },
  });

  const createImpactMutation = useMutation({
    mutationFn: impactApi.create,
    onSuccess: () => {
      message.success('影响研判已创建');
      setImpactModalVisible(false);
      impactForm.resetFields();
      navigate('/impact');
    },
  });

  if (isLoading || !change) {
    return <div className="page-container"><Spin size="large" /></div>;
  }

  const handleReviewSubmit = () => {
    reviewForm.validateFields().then(values => {
      submitReviewMutation.mutate({
        status: values.status,
        decision: values.decision,
        notes: values.notes,
        tags: values.tags || [],
      });
    });
  };

  const handleImpactSubmit = () => {
    impactForm.validateFields().then(values => {
      createImpactMutation.mutate({
        change_id: id!,
        ...values,
        affected_teams: values.affected_teams ? values.affected_teams.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
        affected_systems: values.affected_systems ? values.affected_systems.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
        compliance_areas: values.compliance_areas ? values.compliance_areas.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
      });
    });
  };

  const tabItems = [
    {
      key: 'diff',
      label: '内容差异对比',
      children: (
        <div>
          {diffLoading ? (
            <Spin />
          ) : diffData ? (
            <div>
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={6}>
                  <Statistic title="变更行数" value={diffData.stats.lines_changed} />
                </Col>
                <Col span={6}>
                  <Statistic title="新增行" value={diffData.stats.lines_added} valueStyle={{ color: '#52c41a' }} />
                </Col>
                <Col span={6}>
                  <Statistic title="删除行" value={diffData.stats.lines_removed} valueStyle={{ color: '#ff4d4f' }} />
                </Col>
                <Col span={6}>
                  <Statistic title="变更比例" value={`${(diffData.stats.change_ratio * 100).toFixed(1)}%`} />
                </Col>
              </Row>
              <div className="diff-viewer" dangerouslySetInnerHTML={{ __html: diffData.diff_html }} />
            </div>
          ) : (
            <Text type="secondary">暂无差异数据</Text>
          )}
        </div>
      ),
    },
    {
      key: 'sections',
      label: '变更段落',
      children: (
        <div>
          {diffData?.sections?.map((section, idx) => (
            <Card key={idx} size="small" style={{ marginBottom: 12 }} title={section.header}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div>
                  <Text type="secondary">之前版本：</Text>
                  <div style={{ background: '#fff2f0', padding: 8, borderRadius: 4, marginTop: 4, whiteSpace: 'pre-wrap', fontSize: 13 }}>
                    {section.before_context || '(无)'}
                  </div>
                </div>
                <div>
                  <Text type="secondary">当前版本：</Text>
                  <div style={{ background: '#f6ffed', padding: 8, borderRadius: 4, marginTop: 4, whiteSpace: 'pre-wrap', fontSize: 13 }}>
                    {section.after_context || '(无)'}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ),
    },
  ];

  return (
    <div className="page-container">
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/changes')}>返回列表</Button>
      </Space>

      <Card>
        <Descriptions title={change.title} column={2} bordered size="small">
          <Descriptions.Item label="法规">{change.regulation_title || '-'}</Descriptions.Item>
          <Descriptions.Item label="来源">{change.source_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="变更类型">
            <Tag>{changeTypeLabels[change.change_type] || change.change_type}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="严重程度">
            <span className={`severity-${change.severity}`}>
              {change.severity === 'critical' ? '严重' : change.severity === 'high' ? '高' : change.severity === 'medium' ? '中' : '低'}
            </span>
          </Descriptions.Item>
          <Descriptions.Item label="复核状态">
            <Tag color={change.is_reviewed ? 'green' : 'orange'}>
              {change.is_reviewed ? '已复核' : '待复核'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="检测时间">
            {dayjs(change.created_at).format('YYYY-MM-DD HH:mm:ss')}
          </Descriptions.Item>
          {change.summary && (
            <Descriptions.Item label="变更摘要" span={2}>
              <Paragraph>{change.summary}</Paragraph>
            </Descriptions.Item>
          )}
        </Descriptions>

        <Divider />

        <Space>
          {!change.is_reviewed && (
            <Button
              type="primary"
              icon={<AuditOutlined />}
              onClick={() => setReviewModalVisible(true)}
            >
              提交复核
            </Button>
          )}
          <Button
            icon={<AlertOutlined />}
            onClick={() => setImpactModalVisible(true)}
          >
            创建影响研判
          </Button>
          <Button
            icon={<CheckOutlined />}
            onClick={() => markReviewedMutation.mutate(id!)}
            disabled={change.is_reviewed}
          >
            标记已复核
          </Button>
        </Space>
      </Card>

      <Card style={{ marginTop: 16 }}>
        <Tabs items={tabItems} />
      </Card>

      <Modal
        title="提交复核结论"
        open={reviewModalVisible}
        onOk={handleReviewSubmit}
        onCancel={() => setReviewModalVisible(false)}
        confirmLoading={submitReviewMutation.isPending}
      >
        <Form form={reviewForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="status" label="复核结论" rules={[{ required: true }]} initialValue="confirmed">
            <Select>
              <Option value="confirmed">确认变更</Option>
              <Option value="dismissed">忽略（无实质变化）</Option>
              <Option value="escalated">升级处理</Option>
            </Select>
          </Form.Item>
          <Form.Item name="decision" label="复核决定说明">
            <TextArea rows={3} placeholder="说明复核结论和依据" />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <TextArea rows={2} />
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Select mode="tags" placeholder="输入标签后回车" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="创建影响研判"
        open={impactModalVisible}
        onOk={handleImpactSubmit}
        onCancel={() => setImpactModalVisible(false)}
        width={600}
        confirmLoading={createImpactMutation.isPending}
      >
        <Form form={impactForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="overall_level" label="影响等级" initialValue="medium" rules={[{ required: true }]}>
            <Select>
              <Option value="low">低</Option>
              <Option value="medium">中</Option>
              <Option value="high">高</Option>
              <Option value="critical">严重</Option>
            </Select>
          </Form.Item>
          <Form.Item name="affected_teams" label="受影响团队（逗号分隔）">
            <Input placeholder="合规部, 风控部, 技术部" />
          </Form.Item>
          <Form.Item name="affected_systems" label="受影响系统（逗号分隔）">
            <Input placeholder="风控系统, 合规审查平台" />
          </Form.Item>
          <Form.Item name="compliance_areas" label="合规领域（逗号分隔）">
            <Input placeholder="数据安全, 个人信息保护" />
          </Form.Item>
          <Form.Item name="analysis" label="影响分析">
            <TextArea rows={4} placeholder="分析该变更对业务的具体影响" />
          </Form.Item>
          <Form.Item name="required_actions" label="需采取行动">
            <TextArea rows={3} placeholder="列出需要完成的整改措施" />
          </Form.Item>
          <Form.Item name="estimated_effort" label="预估工作量">
            <Input placeholder="例如：3人天" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
