export type Role = 'admin' | 'analyst' | 'viewer'

export interface User {
  id: number
  username: string
  role: Role
  must_change_password: boolean
  created_at: string
}

export const roleLabel: Record<Role, string> = {
  admin: '管理员',
  analyst: '分析师',
  viewer: '只读',
}

export function useCurrentUser(): User | null {
  try {
    const raw = localStorage.getItem('regintel_user')
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}

export interface Source {
  id: number
  name: string
  base_url: string
  allowed_paths: string[]
  frequency_minutes: number
  enabled: boolean
  respect_robots: boolean
  max_pages: number
  last_run_at: string | null
  created_at: string
}

export interface Run {
  id: number
  source_id: number
  source_name: string
  status: 'running' | 'success' | 'failed'
  started_at: string
  finished_at: string | null
  pages_fetched: number
  attachments_fetched: number
  changes_detected: number
  error: string | null
}

export type ChangeType = 'new' | 'content_updated' | 'attachment_updated'
export type ChangeStatus = 'pending_review' | 'confirmed' | 'dismissed'

export interface ChangeItem {
  id: number
  regulation_id: number
  regulation_title: string
  document_url: string
  source_name: string
  change_type: ChangeType
  status: ChangeStatus
  diff_summary: string
  detected_at: string
}

export interface Attachment {
  id: number
  url: string
  filename: string
  content_hash: string
  created_at: string
}

export interface AttachmentVersion {
  id: number
  url: string
  filename: string
  content_hash: string
  created_at: string
  text: string | null
}

export interface AttachmentDiff {
  old: AttachmentVersion | null
  new: AttachmentVersion | null
  unified_diff: string | null
}

export interface Review {
  reviewer: string
  decision: string
  comment: string | null
  decided_at: string
}

export interface ChangeDetail extends ChangeItem {
  old_text: string | null
  new_text: string | null
  unified_diff: string | null
  attachments: Attachment[]
  attachment_diff: AttachmentDiff | null
  review: Review | null
}

export interface Regulation {
  id: number
  canonical_title: string
  regulation_no: string | null
  authority: string | null
  change_count: number
  pending_count: number
  latest_change_at: string | null
}

export type ImpactLevel = 'high' | 'medium' | 'low'

export interface Assessment {
  id: number
  change_id: number
  regulation_title: string
  business_area: string
  impact_level: ImpactLevel
  analysis: string
  recommendation: string | null
  created_by: string
  created_at: string
}

export interface Subscription {
  id: number
  name: string
  channel: 'webhook' | 'email'
  target: string
  keywords: string[]
  source_ids: number[]
  enabled: boolean
  created_at: string
}

export interface Notification {
  id: number
  subscription_id: number
  subscription_name: string
  change_id: number
  change_title: string
  channel: string
  status: 'sent' | 'failed'
  error: string | null
  created_at: string
  sent_at: string | null
}

export function fmtDate(s: string | null): string {
  if (!s) return '—'
  return new Date(s).toLocaleString('zh-CN')
}
