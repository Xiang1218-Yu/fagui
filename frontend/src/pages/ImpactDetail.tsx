import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card, Button, Spin, Tag, Descriptions, Form, Input, Select,
  Space, message, Typography, Divider,
} from 'antd';
import { ArrowLeftOutlined, SaveOutlined, SendOutlined } from '@ant-design/icons';
import { impactApi } from '../api';
import dayjs from 'dayjs';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;
const { Option } = Select;

const levelConfig: Record<string, { color: string; label: string }> = {
  none: { color: 'default', label: '无影响' },
  low: { color: 'green', label: '低' },
  medium: { color: 'gold', label: '中' },
  high: { color: 'orange', label: '高' },
  critical: { color: 'red', label: '严重' },
};

export default function ImpactDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form] = Form.useForm();

  const { data: assessment, isLoading } = useQuery({
    queryKey: ['impact-assessment', id],
    queryFn: () => impactApi.get(id!),
    enabled: !!id,
  });

  const updateMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => impactApi.update(id!, data),
    onSuccess: () => {
      message.success('研判记录已保存');
      queryClient.invalidateQueries({ queryKey: ['impact-assessment', id] });
    },
  });

  const submitMutation = useMutation({
    mutationFn: () => impactApi.submit(id!),
    onSuccess: () => {
      message.success('研判报告已提交');
      queryClient.invalidateQueries({ queryKey: ['impact-assessment', id] });
    },
  });

  if (isLoading || !assessment) {
    return <div className="page-container"><Spin size="large" /></div>;
  }

  const handleSave = () => {
    form.validateFields().then(values => {
      updateMutation.mutate({
        ...values,
        affected_teams: values.affected_teams ? values.affected_teams.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
        affected_systems: values.affected_systems ? values.affected_systems.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
        affected_products: values.affected_products ? values.affected_products.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
        compliance_areas: values.compliance_areas ? values.compliance_areas.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
      });
    });
  };

  return (
    <div className="page-container">
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/impact')}>
          返回列表
        </Button>
      </Space>

      <Card>
        <Descriptions title="影响研判详情" column={2} bordered size="small">
          <Descriptions.Item label="法规 ID">
            <Text code copyable>{assessment.regulation_id}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="关联变更">
            {assessment.change_id ? <Tag color="blue">变更记录</Tag> : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="当前影响等级">
            <Tag color={levelConfig[assessment.overall_level]?.color}>
              {levelConfig[assessment.overall_level]?.label}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag>{assessment.status === 'draft' ? '草稿' : '已提交'}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="评估人">
            {assessment.assessor_name || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="截止日期">
            {assessment.deadline ? dayjs(assessment.deadline).format('YYYY-MM-DD') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="预估工作量">
            {assessment.estimated_effort || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {dayjs(assessment.updated_at).format('YYYY-MM-DD HH:mm')}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card style={{ marginTop: 16 }} title="编辑研判内容">
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            ...assessment,
            affected_teams: assessment.affected_teams?.join(', '),
            affected_systems: assessment.affected_systems?.join(', '),
            affected_products: assessment.affected_products?.join(', '),
            compliance_areas: assessment.compliance_areas?.join(', '),
          }}
        >
          <div className="assessment-section">
            <div className="section-title">影响等级</div>
            <Form.Item name="overall_level" rules={[{ required: true }]}>
              <Select style={{ width: 200 }}>
                <Option value="low">低 - 微小调整即可满足</Option>
                <Option value="medium">中 - 需要部分系统或流程调整</Option>
                <Option value="high">高 - 需要跨部门整改</Option>
                <Option value="critical">严重 - 立即行动，可能影响业务合规</Option>
              </Select>
            </Form.Item>
          </div>

          <Divider />

          <div className="assessment-section">
            <div className="section-title">影响范围</div>
            <Form.Item name="affected_teams" label="受影响团队（逗号分隔）">
              <Input placeholder="合规部, 风控部, 技术部" />
            </Form.Item>
            <Form.Item name="affected_systems" label="受影响系统（逗号分隔）">
              <Input placeholder="风控系统, 用户中心, 合规审查平台" />
            </Form.Item>
            <Form.Item name="affected_products" label="受影响产品（逗号分隔）">
              <Input placeholder="信贷产品, 支付产品" />
            </Form.Item>
            <Form.Item name="compliance_areas" label="合规领域（逗号分隔）">
              <Input placeholder="数据安全, 个人信息保护, 反洗钱" />
            </Form.Item>
          </div>

          <Divider />

          <div className="assessment-section">
            <div className="section-title">分析与行动</div>
            <Form.Item name="analysis" label="影响分析">
              <TextArea rows={5} placeholder="详细分析该法规变更对业务流程、系统功能、数据处理等方面的具体影响" />
            </Form.Item>
            <Form.Item name="required_actions" label="需采取行动">
              <TextArea rows={4} placeholder="列出为满足新法规要求需要完成的整改措施、负责人和时间节点" />
            </Form.Item>
            <Form.Item name="estimated_effort" label="预估工作量">
              <Input placeholder="例如：3人天" style={{ width: 200 }} />
            </Form.Item>
          </div>

          <Space>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={updateMutation.isPending}
            >
              保存草稿
            </Button>
            {assessment.status === 'draft' && (
              <Button
                type="primary"
                danger
                icon={<SendOutlined />}
                onClick={() => { handleSave(); submitMutation.mutate(); }}
                loading={submitMutation.isPending}
              >
                保存并提交
              </Button>
            )}
          </Space>
        </Form>
      </Card>
    </div>
  );
}
