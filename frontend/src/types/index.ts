export interface Source {
  id: string;
  name: string;
  url: string;
  base_url: string;
  source_type: 'regulatory' | 'association' | 'consultation' | 'other';
  status: 'active' | 'paused' | 'error';
  crawl_frequency_minutes: number;
  max_depth: number;
  allowed_paths: string[];
  excluded_paths: string[];
  selector_config: Record<string, unknown>;
  robots_txt_enabled: boolean;
  respect_crawl_delay: boolean;
  headers: Record<string, string>;
  description?: string;
  last_crawled_at?: string;
  last_error?: string;
  created_at: string;
  updated_at: string;
}

export interface CrawlRun {
  id: string;
  source_id: string;
  source_name?: string;
  status: 'pending' | 'running' | 'success' | 'partial' | 'failed';
  triggered_by: string;
  started_at?: string;
  completed_at?: string;
  pages_crawled: number;
  pages_failed: number;
  attachments_downloaded: number;
  new_regulations: number;
  changes_detected: number;
  error_message?: string;
  celery_task_id?: string;
  created_at: string;
}

export interface Regulation {
  id: string;
  source_id: string;
  source_name?: string;
  title: string;
  url: string;
  regulation_number?: string;
  issuing_authority?: string;
  publish_date?: string;
  effective_date?: string;
  status: string;
  summary?: string;
  is_primary: boolean;
  merge_group_id?: string;
  merge_confidence?: number;
  first_seen_at: string;
  last_seen_at: string;
  created_at: string;
  updated_at: string;
}

export interface Change {
  id: string;
  regulation_id: string;
  regulation_title?: string;
  source_name?: string;
  crawl_run_id: string;
  previous_snapshot_id?: string;
  current_snapshot_id?: string;
  change_type: 'new' | 'content_update' | 'attachment_update' | 'status_change' | 'repeal';
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  summary?: string;
  diff_stats: Record<string, number>;
  changed_fields: unknown[];
  attachment_changes: unknown[];
  is_reviewed: boolean;
  review_status?: string;
  created_at: string;
}

export interface Review {
  id: string;
  change_id: string;
  regulation_id: string;
  status: 'pending' | 'in_review' | 'confirmed' | 'dismissed' | 'escalated';
  reviewer_id?: string;
  reviewer_name?: string;
  decision?: string;
  notes?: string;
  tags: string[];
  assigned_at?: string;
  claimed_at?: string;
  completed_at?: string;
  due_at?: string;
  created_at: string;
  updated_at: string;
  change?: Change;
}

export interface ImpactAssessment {
  id: string;
  regulation_id: string;
  change_id?: string;
  assessor_id?: string;
  assessor_name?: string;
  overall_level: 'none' | 'low' | 'medium' | 'high' | 'critical';
  affected_teams: string[];
  affected_systems: string[];
  affected_products: string[];
  compliance_areas: string[];
  analysis?: string;
  required_actions?: string;
  deadline?: string;
  estimated_effort?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Subscription {
  id: string;
  name: string;
  user_id: string;
  user_name?: string;
  user_email?: string;
  source_id?: string;
  keywords: string[];
  severity_filter: string[];
  channels: string[];
  is_active: boolean;
  last_notified_at?: string;
  created_at: string;
  updated_at: string;
}

export interface Notification {
  id: string;
  subscription_id: string;
  change_id?: string;
  channel: string;
  status: string;
  title: string;
  content?: string;
  recipient?: string;
  sent_at?: string;
  read_at?: string;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DashboardStats {
  total_sources: number;
  active_sources: number;
  total_regulations: number;
  pending_reviews: number;
  in_review_count: number;
  changes_today: number;
  changes_this_week: number;
  severity_breakdown: Record<string, number>;
  review_breakdown: Record<string, number>;
  source_type_breakdown: Record<string, number>;
  recent_crawls: Array<{
    id: string;
    source_name: string;
    status: string;
    pages_crawled: number;
    changes_detected: number;
    started_at?: string;
    completed_at?: string;
  }>;
  recent_changes: Array<{
    id: string;
    title: string;
    severity: string;
    change_type: string;
    regulation_title?: string;
    source_name?: string;
    created_at: string;
  }>;
}

export interface DiffResult {
  change_id: string;
  before_text: string;
  after_text: string;
  diff_html: string;
  unified_diff: string[];
  stats: {
    lines_added: number;
    lines_removed: number;
    lines_changed: number;
    total_before: number;
    total_after: number;
    change_ratio: number;
  };
  sections: Array<{
    section_type: string;
    header: string;
    before_context: string;
    after_context: string;
    lines: Array<{ type: string; text: string }>;
  }>;
  severity: string;
}
