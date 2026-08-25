import type { ChangeType, ImpactLevel, ReviewStatus, RunStatus, SourceType } from './types'

export const fmtTime = (s: string | null) =>
  s ? new Date(s).toLocaleString('zh-CN', { hour12: false }) : '—'

export const sourceTypeLabel: Record<SourceType, string> = {
  regulator: '监管网站',
  association: '行业协会',
  consultation: '征求意见',
}

export const runStatusLabel: Record<RunStatus, string> = {
  pending: '待执行',
  running: '运行中',
  success: '成功',
  failed: '失败',
  skipped: '已跳过',
}

export const runStatusBadge: Record<RunStatus, string> = {
  pending: 'badge-gray',
  running: 'badge-blue',
  success: 'badge-green',
  failed: 'badge-red',
  skipped: 'badge-amber',
}

export const changeTypeLabel: Record<ChangeType, string> = {
  new: '新增法规',
  body_changed: '正文变化',
  attachment_changed: '附件变化',
  metadata_changed: '修订记录变化',
}

export const changeTypeBadge: Record<ChangeType, string> = {
  new: 'badge-blue',
  body_changed: 'badge-amber',
  attachment_changed: 'badge-amber',
  metadata_changed: 'badge-gray',
}

export const reviewStatusLabel: Record<ReviewStatus, string> = {
  pending: '待复核',
  confirmed: '已确认',
  dismissed: '已忽略',
}

export const reviewStatusBadge: Record<ReviewStatus, string> = {
  pending: 'badge-amber',
  confirmed: 'badge-green',
  dismissed: 'badge-gray',
}

export const impactLabel: Record<ImpactLevel, string> = {
  unassessed: '未研判',
  low: '低',
  medium: '中',
  high: '高',
}

export const impactBadge: Record<ImpactLevel, string> = {
  unassessed: 'badge-gray',
  low: 'badge-blue',
  medium: 'badge-amber',
  high: 'badge-red',
}
