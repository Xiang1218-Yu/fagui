export const CHANGE_TYPE_LABELS: Record<string, string> = {
  new: '新法规/新页面',
  content_modified: '正文修订',
  attachment_modified: '附件变更',
  title_modified: '标题变更',
  unpublished: '页面下线',
}

export const CHANGE_STATUS_LABELS: Record<string, string> = {
  pending_review: '待复核',
  confirmed: '已确认',
  dismissed: '已驳回',
}

export const RUN_STATUS_LABELS: Record<string, string> = {
  pending: '排队中',
  running: '采集中',
  success: '成功',
  failed: '失败',
  partial: '部分成功',
}

export const REVIEW_STATUS_LABELS: Record<string, string> = {
  pending: '待认领',
  claimed: '复核中',
  approved: '已出结论',
  dismissed: '已驳回',
}

export const SEVERITY_LABELS: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
}

export const ORG_TYPE_LABELS: Record<string, string> = {
  regulator: '监管机构',
  association: '行业协会',
  consultation: '公开征求意见',
  platform: '转载平台',
}

export const FREQUENCY_LABELS: Record<string, string> = {
  hourly: '每小时',
  every_6h: '每6小时',
  daily: '每天',
  weekly: '每周',
}

export const EVENT_TYPE_LABELS: Record<string, string> = {
  change_detected: '检测到法规变更',
  review_decided: '复核结论出具',
  impact_published: '影响研判发布',
}

export function tagColor(map: Record<string, string>, value: string): string {
  const colors = ['blue', 'green', 'orange', 'red', 'purple', 'cyan', 'magenta']
  const keys = Object.keys(map)
  const idx = Math.max(keys.indexOf(value), 0)
  return colors[idx % colors.length]
}

export const SEVERITY_COLORS: Record<string, string> = {
  high: 'red',
  medium: 'orange',
  low: 'default',
}

export const RUN_STATUS_COLORS: Record<string, string> = {
  pending: 'default',
  running: 'processing',
  success: 'green',
  failed: 'error',
  partial: 'warning',
}

export const CHANGE_STATUS_COLORS: Record<string, string> = {
  pending_review: 'orange',
  confirmed: 'green',
  dismissed: 'default',
}
