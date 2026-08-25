import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card, Button, Spin, Tag, Descriptions, Tabs, Typography, Space,
  Modal, Form, Input, Select, message, Divider, Statistic, Row, Col,
  List, Empty, Alert,
} from 'antd';
import {
  ArrowLeftOutlined, CheckOutlined,
  AlertOutlined, AuditOutlined,
  PaperClipOutlined, FileAddOutlined, DeleteOutlined, EditOutlined,
} from '@ant-design/icons';
import { changesApi, reviewsApi, impactApi } from '../api';
import type { Change, Review } from '../types';
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

const severityLabels: Record<string, { text: string; color: string }> = {
  critical: { text: '严重', color: '#cf1322' },
  high: { text: '高', color: '#fa541c' },
  medium: { text: '中', color: '#faad14' },
  low: { text: '低', color: '#52c41a' },
};

const reviewStatusLabels: Record<string, { text: string; color: string }> = {
  pending: { text: '待复核', color: 'orange' },
  in_review: { text: '复核中', color: 'blue' },
  confirmed: { text: '已确认', color: 'green' },
  dismissed: { text: '已忽略', color: 'default' },
  escalated: { text: '已升级', color: 'red' },
};

export default function ChangeDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [reviewModalVisible, setReviewModalVisible] = useState(false);
  const [impactModalVisible, setImpactModalVisible] = useState(false);
  const [reviewForm] = Form.useForm();
  const [impactForm] = Form.useForm();

  const { data: change, isLoading } = useQuery<Change>({
    queryKey: ['change', id],
    queryFn: () => changesApi.get(id!),
    enabled: !!id,
  });

  const { data: diffData, isLoading: diffLoading } = useQuery({
    queryKey: ['change-diff', id],
    queryFn: () => changesApi.getDiff(id!),
    enabled: !!id && change?.change_type === 'content_update',
  });

  const { data: reviewData } = useQuery({
    queryKey: ['review-by-change', id],
    queryFn: () => reviewsApi.getByChangeId(id!),
    enabled: !!id,
    retry: false,
  });

  const markReviewedMutation = useMutation({
    mutationFn: changesApi.markReviewed,
    onSuccess: () => {
      message.success('已标记为已复核');
      queryClient.invalidateQueries({ queryKey: ['change', id] });
      queryClient.invalidateQueries({ queryKey: ['review-by-change', id] });
    },
  });

  const submitReviewMutation = useMutation({
    mutationFn: (data: { reviewId: string; status: Review['status']; decision: string; notes: string; tags: string[] }) => {
      const { reviewId, ...payload } = data;
      return reviewsApi.update(reviewId, payload);
    },
    onSuccess: () => {
      message.success('复核结论已提交');
      setReviewModalVisible(false);
      reviewForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['change', id] });
      queryClient.invalidateQueries({ queryKey: ['review-by-change', id] });
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(msg || '复核提交失败');
    },
  });

  const claimReviewMutation = useMutation({
    mutationFn: (reviewId: string) =>
      reviewsApi.claim(reviewId, 'analyst@compliance', '合规分析师'),
    onSuccess: () => {
      message.success('已领取复核任务');
      queryClient.invalidateQueries({ queryKey: ['review-by-change', id] });
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

  const reviewId = change.review_id || reviewData?.id;
  const reviewStatus = reviewData?.status || change.review_status;
  const isReviewed = change.is_reviewed || reviewStatus === 'confirmed' || reviewStatus === 'dismissed';

  const handleReviewSubmit = () => {
    if (!reviewId) {
      message.error('未找到关联的复核记录，无法提交');
      return;
    }
    reviewForm.validateFields().then(values => {
      submitReviewMutation.mutate({
        reviewId,
        status: values.status as Review['status'],
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

  const attachmentChanges = (change.attachment_changes as {
    added?: Array<{ filename: string; url: string }>;
    removed?: Array<{ filename: string; url: string }>;
    modified?: Array<{ filename: string; url: string }>;
  }) || {};

  const hasAttachmentChanges =
    (attachmentChanges.added?.length || 0) +
    (attachmentChanges.removed?.length || 0) +
    (attachmentChanges.modified?.length || 0) > 0;

  const tabItems = [
    ...(change.change_type === 'content_update' ? [{
      key: 'diff',
      label: '内容差异对比',
      children: (
        <div>
          {diffLoading ? (
            <Spin />
          ) : diffData ? (
            <div>
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={6}><Statistic title="变更行数" value={diffData.stats.lines_changed} /></Col>
                <Col span={6}><Statistic title="新增行" value={diffData.stats.lines_added} valueStyle={{ color: '#52c41a' }} /></Col>
                <Col span={6}><Statistic title="删除行" value={diffData.stats.lines_removed} valueStyle={{ color: '#ff4d4f' }} /></Col>
                <Col span={6}><Statistic title="变更比例" value={`${(diffData.stats.change_ratio * 100).toFixed(1)}%`} /></Col>
              </Row>
              <div className="diff-viewer" dangerouslySetInnerHTML={{ __html: diffData.diff_html }} />
            </div>
          ) : (
            <Text type="secondary">暂无差异数据</Text>
          )}
        </div>
      ),
    }] : []),
    ...(change.change_type === 'content_update' && diffData?.sections?.length ? [{
      key: 'sections',
      label: '变更段落',
      children: (
        <div>
          {diffData.sections.map((section: { header: string; before_context: string; after_context: string }, idx: number) => (
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
    }] : []),
    ...(change.change_type === 'attachment_update' ? [{
      key: 'attachments',
      label: <span><PaperClipOutlined /> 附件变更明细</span>,
      children: hasAttachmentChanges ? (
        <div>
          {attachmentChanges.added && attachmentChanges.added.length > 0 && (
            <Card size="small" title={<span><FileAddOutlined style={{ color: '#52c41a' }} /> 新增附件 ({attachmentChanges.added.length})</span>} style={{ marginBottom: 12 }}>
              <List
                size="small"
                dataSource={attachmentChanges.added}
                renderItem={item => (
                  <List.Item>
                    <a href={item.url} target="_blank" rel="noreferrer">{item.filename}</a>
                  </List.Item>
                )}
              />
            </Card>
          )}
          {attachmentChanges.removed && attachmentChanges.removed.length > 0 && (
            <Card size="small" title={<span><DeleteOutlined style={{ color: '#ff4d4f' }} /> 删除附件 ({attachmentChanges.removed.length})</span>} style={{ marginBottom: 12 }}>
              <List
                size="small"
                dataSource={attachmentChanges.removed}
                renderItem={item => (
                  <List.Item>
                    <Text delete>{item.filename}</Text>
                  </List.Item>
                )}
              />
            </Card>
          )}
          {attachmentChanges.modified && attachmentChanges.modified.length > 0 && (
            <Card size="small" title={<span><EditOutlined style={{ color: '#faad14' }} /> 修改附件 ({attachmentChanges.modified.length})</span>}>
              <List
                size="small"
                dataSource={attachmentChanges.modified}
                renderItem={item => (
                  <List.Item>
                    <a href={item.url} target="_blank" rel="noreferrer">{item.filename}</a>
                  </List.Item>
                )}
              />
            </Card>
          )}
        </div>
      ) : (
        <Empty description="无附件变更明细" />
      ),
    }] : []),
    ...(change.change_type === 'new' ? [{
      key: 'new-info',
      label: '收录信息',
      children: (
        <Alert
          type="info"
          showIcon
          message="这是首次收录的法规"
          description={
            <div>
              <Paragraph>{change.summary}</Paragraph>
              <Paragraph>系统已自动创建快照并纳入法规库，可前往法规详情页查看完整内容和附件。</Paragraph>
              <Button type="link" onClick={() => navigate(`/regulations`)}>查看法规库</Button>
            </div>
          }
        />
      ),
    }] : []),
  ];

  const sevCfg = severityLabels[change.severity] || severityLabels.medium;
  const revCfg = reviewStatus ? (reviewStatusLabels[reviewStatus] || { text: reviewStatus, color: 'default' }) : null;

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
            <Tag color="blue">{changeTypeLabels[change.change_type] || change.change_type}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="严重程度">
            <span style={{ color: sevCfg.color, fontWeight: 600 }}>{sevCfg.text}</span>
          </Descriptions.Item>
          <Descriptions.Item label="复核状态">
            {revCfg ? <Tag color={revCfg.color}>{revCfg.text}</Tag> : <Tag>无复核记录</Tag>}
          </Descriptions.Item>
          <Descriptions.Item label="复核 ID">
            {reviewId ? <Text code copyable>{reviewId.slice(0, 8)}...</Text> : <Text type="secondary">未生成</Text>}
          </Descriptions.Item>
          <Descriptions.Item label="检测时间">
            {dayjs(change.created_at).format('YYYY-MM-DD HH:mm:ss')}
          </Descriptions.Item>
          {reviewData?.reviewer_name && (
            <Descriptions.Item label="复核人">{reviewData.reviewer_name}</Descriptions.Item>
          )}
          {change.summary && (
            <Descriptions.Item label="变更摘要" span={2}>
              <Paragraph>{change.summary}</Paragraph>
            </Descriptions.Item>
          )}
          {reviewData?.decision && (
            <Descriptions.Item label="复核决定" span={2}>
              <Paragraph>{reviewData.decision}</Paragraph>
            </Descriptions.Item>
          )}
          {reviewData?.notes && (
            <Descriptions.Item label="备注" span={2}>
              <Paragraph>{reviewData.notes}</Paragraph>
            </Descriptions.Item>
          )}
        </Descriptions>

        <Divider />

        <Space wrap>
          {reviewId && reviewStatus === 'pending' && (
            <Button
              icon={<AuditOutlined />}
              onClick={() => claimReviewMutation.mutate(reviewId)}
              loading={claimReviewMutation.isPending}
            >
              领取复核
            </Button>
          )}
          {reviewId && !isReviewed && (
            <Button
              type="primary"
              icon={<AuditOutlined />}
              onClick={() => setReviewModalVisible(true)}
            >
              {reviewStatus === 'in_review' ? '提交复核结论' : '处理复核'}
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
            disabled={isReviewed}
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
        {!reviewId && (
          <Alert type="warning" message="未找到关联的复核记录" style={{ marginBottom: 16 }} showIcon />
        )}
        <Form form={reviewForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="status" label="复核结论" rules={[{ required: true }]} initialValue="confirmed">
            <Select>
              <Option value="confirmed">确认变更（需要跟进）</Option>
              <Option value="dismissed">忽略（无实质变化）</Option>
              <Option value="escalated">升级处理（重大变化）</Option>
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
