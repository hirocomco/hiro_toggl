// API response types based on the backend schemas

export interface DateRange {
  start: string
  end: string
  description?: string
}

export interface ReportTotals {
  total_hours: number
  billable_hours: number
  entry_count: number
  total_earnings_usd?: number
  total_earnings_eur?: number
  billable_earnings_usd?: number
  billable_earnings_eur?: number
  billable_percentage?: number
  average_hourly_rate_usd?: number
  average_hourly_rate_eur?: number
}

export interface MemberReportData {
  member_id: number
  member_name: string
  total_hours: number
  billable_hours: number
  entry_count: number
  total_earnings_usd?: number
  total_earnings_eur?: number
  billable_earnings_usd?: number
  billable_earnings_eur?: number
  hourly_rate_usd?: number
  hourly_rate_eur?: number
}

export interface ProjectReportData {
  project_id?: number
  project_name: string
  total_hours: number
  billable_hours: number
  entry_count: number
  total_earnings_usd?: number
  total_earnings_eur?: number
  billable_earnings_usd?: number
  billable_earnings_eur?: number
  members: MemberReportData[]
}

export interface ClientReportData {
  client_id?: number
  client_name: string
  total_hours: number
  billable_hours: number
  total_earnings_usd?: number
  total_earnings_eur?: number
  billable_earnings_usd?: number
  billable_earnings_eur?: number
  project_count: number
  member_reports: MemberReportData[]
  billable_percentage?: number
}

export interface WorkspaceReportResponse {
  workspace_id: number
  date_range: DateRange
  totals: ReportTotals
  summary: {
    total_clients: number
    total_members: number
    total_projects: number
    clients_with_time: number
  }
  client_reports: ClientReportData[]
  generated_at: string
  report_type: string
}

export interface ClientDetailResponse {
  client_id?: number
  client_name: string
  workspace_id: number
  date_range: DateRange
  totals: ReportTotals
  projects: ProjectReportData[]
  generated_at: string
  report_type: string
}

export interface MemberPerformanceResponse {
  member_id: number
  member_name: string
  workspace_id: number
  date_range: DateRange
  totals: ReportTotals
  clients: Array<{
    client_id?: number
    client_name: string
    total_hours: number
    billable_hours: number
    entry_count: number
    total_earnings_usd?: number
    total_earnings_eur?: number
    billable_earnings_usd?: number
    billable_earnings_eur?: number
    hourly_rate_usd?: number
    hourly_rate_eur?: number
  }>
  generated_at: string
  report_type: string
}

export interface TimeEntryDetail {
  id: number
  description: string
  duration_hours: number
  start_time: string
  stop_time?: string
  user_name: string
  project_name?: string
  client_name?: string
  billable: boolean
  tags: string[]
  earnings_usd?: number
  earnings_eur?: number
}

export interface DrillDownResponse {
  workspace_id: number
  filters: Record<string, any>
  total_entries: number
  entries: TimeEntryDetail[]
  pagination: {
    limit: number
    offset: number
    total_pages: number
    current_page: number
  }
  summary: ReportTotals
  generated_at: string
}

// Request types
export type ReportPeriod = 
  | 'last_7_days'
  | 'last_30_days'
  | 'last_90_days'
  | 'this_month'
  | 'last_month'
  | 'this_quarter'
  | 'last_quarter'
  | 'this_year'
  | 'custom'

export type ReportCurrency = 'usd' | 'eur' | 'both'

export interface ReportRequest {
  workspace_id: number
  period?: ReportPeriod
  start_date?: string
  end_date?: string
  client_ids?: number[]
  member_ids?: number[]
  include_non_billable?: boolean
  include_financial?: boolean
  currency?: ReportCurrency
}

export interface ClientReportRequest extends ReportRequest {
  include_project_breakdown?: boolean
  sort_by?: 'total_hours' | 'billable_hours' | 'total_earnings_usd' | 'total_earnings_eur' | 'client_name'
  sort_order?: 'asc' | 'desc'
}

export interface DrillDownRequest {
  workspace_id: number
  client_id?: number
  member_id?: number
  project_id?: number
  start_date?: string
  end_date?: string
  billable_only?: boolean
  limit?: number
  offset?: number
  sort_by?: 'start_time' | 'duration' | 'description' | 'user_name' | 'project_name' | 'client_name'
  sort_order?: 'asc' | 'desc'
}

// Rate management types
export interface Rate {
  id: number
  member_id: number
  member_name?: string
  client_id?: number
  client_name?: string
  hourly_rate_usd?: number
  hourly_rate_eur?: number
  effective_date: string
  created_at: string
  updated_at: string
}

export interface RateCreate {
  member_id: number
  client_id?: number
  hourly_rate_usd?: number
  hourly_rate_eur?: number
  effective_date?: string
}

export interface Member {
  id: number
  toggl_id: number
  name: string
  email?: string
  workspace_id: number
  active: boolean
}

export interface Client {
  id: number
  toggl_id: number
  name: string
  workspace_id: number
  archived: boolean
}

// Sync types
export interface SyncLog {
  id: number
  workspace_id: number
  sync_type: string
  status: 'running' | 'completed' | 'failed'
  start_time: string
  end_time?: string
  records_processed: number
  records_added: number
  records_updated: number
  error_message?: string
  date_range_start?: string
  date_range_end?: string
}

export interface SyncStatus {
  workspace_id: number
  recent_syncs: SyncLog[]
  last_full_sync?: SyncLog
  is_sync_running: boolean
}

// Common API response wrapper
export interface ApiResponse<T = any> {
  data?: T
  error?: string
  message?: string
}