export interface UserInfo {
  id: number
  username: string
  display_name: string
  role: 'admin' | 'analyst'
  is_active: boolean
}

export interface Source {
  id: number
  name: string
  org_type: string
  base_url: string
  homepage_url: string
  frequency: string
  interval_minutes: number
  enabled: boolean
  respect_robots: boolean
  allowed_paths: string[]
  max_depth: number
  description: string
  status: string
  last_crawled_at: string | null
  created_at: string
}

export interface CrawlRun {
  id: number
  source_id: number
  trigger_type: string
  status: string
  started_at: string
  finished_at: string | null
  pages_fetched: number
  attachments_fetched: number
  changes_detected: number
  new_regulations: number
  error: string
  stats: Record<string, number>
  log?: string
  source?: Source
}

export interface Regulation {
  id: number
  title: string
  reg_number: string | null
  authority: string
  publish_date: string | null
  effective_date: string | null
  canonical_url: string
  status: string
  summary: string
  tags: string[]
  created_at: string
  updated_at: string
}

export interface DocItem {
  id: number
  source_id: number
  regulation_id: number | null
  parent_id: number | null
  url: string
  title: string
  doc_type: 'page' | 'attachment'
  content_type: string
  attachment_name: string
  content_hash: string
  text_hash: string
  first_seen_at: string
  last_seen_at: string
  source_name?: string
  snapshot_count?: number
}

export interface Snapshot {
  id: number
  document_id: number
  crawl_run_id: number
  fetched_at: string
  status_code: number
  content_type: string
  size_bytes: number
  content_hash: string
  text_hash: string
  title: string
  is_attachment: boolean
  http_error: string
}

export interface Change {
  id: number
  regulation_id: number | null
  document_id: number
  source_id: number
  from_snapshot_id: number | null
  to_snapshot_id: number
  change_type: string
  status: string
  severity: string
  title: string
  summary: string
  changed_fields: Record<string, unknown>
  detected_at: string
  decided_at: string | null
}

export interface DiffRow {
  type: 'equal' | 'replace' | 'delete' | 'insert'
  old_no: number | null
  new_no: number | null
  old: string
  new: string
}

export interface ChangeDetail {
  change: Change
  document: { id: number; url: string; title: string; doc_type: string; attachment_name: string }
  regulation: { id: number; title: string; reg_number: string | null } | null
  source: { id: number; name: string; org_type: string } | null
  review: { id: number; status: string; decision: string; comment: string; assignee_id: number | null } | null
  old_snapshot: {
    id: number
    fetched_at: string
    title: string
    content_hash: string
    text_hash: string
    size_bytes: number
    crawl_run_id: number
  } | null
  new_snapshot: {
    id: number
    fetched_at: string
    title: string
    content_hash: string
    text_hash: string
    size_bytes: number
    crawl_run_id: number
  }
  old_text: string
  new_text: string
  diff_rows: DiffRow[]
}

export interface ReviewTask {
  id: number
  change_id: number
  status: string
  assignee_id: number | null
  assignee_name: string | null
  decision: string
  comment: string
  created_at: string
  claimed_at: string | null
  decided_at: string | null
  change_title: string
  change_type: string
  severity: string
  change_status: string
  summary: string
  source_name: string
  detected_at: string
}

export interface ImpactAssessment {
  id: number
  change_id: number | null
  regulation_id: number | null
  analyst_id: number
  risk_level: string
  affected_teams: string[]
  affected_business: string
  impact_summary: string
  action_items: string[]
  status: string
  created_at: string
  updated_at: string
  change_title?: string
  regulation_title?: string
  analyst_name?: string
}

export interface Subscription {
  id: number
  user_id: number
  name: string
  channel: string
  event_types: string[]
  source_ids: number[]
  keywords: string[]
  destination: string
  enabled: boolean
  created_at: string
}

export interface NotificationItem {
  id: number
  event_type: string
  title: string
  body: string
  data: Record<string, unknown>
  is_read: boolean
  send_status: string
  created_at: string
}

export interface DashboardStats {
  cards: {
    sources_total: number
    sources_enabled: number
    regulations_total: number
    changes_pending: number
    review_pending: number
    runs_24h: number
    unread_notifications: number
  }
  recent_changes: Array<{
    id: number
    title: string
    change_type: string
    status: string
    severity: string
    source_name: string
    detected_at: string
  }>
  recent_runs: Array<{
    id: number
    source_name: string
    status: string
    trigger_type: string
    pages_fetched: number
    changes_detected: number
    started_at: string
    finished_at: string | null
  }>
}
