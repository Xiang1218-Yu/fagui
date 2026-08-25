// Shared TypeScript types mirroring backend schemas.
export type SourceType = 'regulator' | 'association' | 'consultation'
export type RunStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped'
export type ChangeType = 'new' | 'body_changed' | 'attachment_changed' | 'metadata_changed'
export type ReviewStatus = 'pending' | 'confirmed' | 'dismissed'
export type ImpactLevel = 'unassessed' | 'low' | 'medium' | 'high'

export interface Source {
  id: number
  name: string
  url: string
  source_type: SourceType
  allowed_hosts: string
  frequency_minutes: number
  enabled: boolean
  respect_robots: boolean
  fetch_attachments: boolean
  follow_links: boolean
  max_links: number
  link_selector: string
  notes: string
  last_run_at: string | null
  created_at: string
}

export interface CrawlRun {
  id: number
  source_id: number
  status: RunStatus
  trigger: string
  started_at: string | null
  finished_at: string | null
  pages_fetched: number
  attachments_fetched: number
  changes_detected: number
  robots_blocked: number
  message: string
  created_at: string
}

export interface Document {
  id: number
  source_id: number
  url: string
  title: string
  dedup_key: string
  regulation_id: number | null
  latest_body_hash: string
  impact_level: ImpactLevel
  first_seen_at: string
  last_seen_at: string
}

export interface Regulation {
  id: number
  title: string
  dedup_key: string
  identifier: string
  created_at: string
}

export interface ChangeEvent {
  id: number
  document_id: number
  run_id: number
  change_type: ChangeType
  old_snapshot_id: number | null
  new_snapshot_id: number | null
  summary: string
  similarity: number
  created_at: string
  diff_text?: string
  document?: Document | null
}

export interface Snapshot {
  id: number
  run_id: number
  document_id: number
  kind: string
  url: string
  filename: string
  content_type: string
  http_status: number
  content_hash: string
  text_excerpt: string
  captured_at: string
}

export interface ReviewItem {
  id: number
  change_id: number
  status: ReviewStatus
  impact_level: ImpactLevel
  assignee: string
  decision_note: string
  impact_note: string
  affected_business: string
  reviewed_by: string
  reviewed_at: string | null
  created_at: string
  change?: ChangeEvent | null
}

export interface Subscription {
  id: number
  name: string
  subscriber: string
  keyword: string
  source_id: number | null
  min_impact: ImpactLevel
  channel: string
  email: string
  enabled: boolean
  created_at: string
}

export interface Notification {
  id: number
  subscription_id: number | null
  change_id: number | null
  title: string
  body: string
  channel: string
  delivery_status: string
  delivery_detail: string
  is_read: boolean
  created_at: string
}

export interface DashboardStats {
  sources: number
  active_sources: number
  documents: number
  regulations: number
  pending_reviews: number
  changes_last_7d: number
  unread_notifications: number
}
