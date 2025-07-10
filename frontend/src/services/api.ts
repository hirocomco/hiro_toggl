import axios, { AxiosInstance, AxiosResponse } from 'axios'
import {
  WorkspaceReportResponse,
  ClientDetailResponse,
  MemberPerformanceResponse,
  DrillDownResponse,
  ClientReportRequest,
  DrillDownRequest,
  Rate,
  RateCreate,
  Member,
  Client,
  SyncLog,
  SyncStatus,
  ApiResponse
} from '@/types/api'

class ApiService {
  private api: AxiosInstance

  constructor() {
    this.api = axios.create({
      baseURL: '/api',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Add request interceptor for debugging
    this.api.interceptors.request.use(
      (config) => {
        console.log(`🔍 API Request: ${config.method?.toUpperCase()} ${config.url}`, config.data)
        return config
      },
      (error) => {
        console.error('❌ API Request Error:', error)
        return Promise.reject(error)
      }
    )

    // Add response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => {
        console.log(`✅ API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`, response.data)
        return response
      },
      (error) => {
        console.error('❌ API Response Error:', error.response?.data || error.message)
        return Promise.reject(error)
      }
    )
  }

  // Helper method to handle API responses
  private handleResponse<T>(response: AxiosResponse<T>): T {
    return response.data
  }

  // Reports API
  async getWorkspaceReport(request: ClientReportRequest): Promise<WorkspaceReportResponse> {
    const response = await this.api.post<WorkspaceReportResponse>('/reports/workspace', request)
    return this.handleResponse(response)
  }

  async getClientDetail(
    clientId: number | null,
    workspaceId: number,
    params: {
      period?: string
      start_date?: string
      end_date?: string
      include_project_breakdown?: boolean
    } = {}
  ): Promise<ClientDetailResponse> {
    const url = `/reports/client/${clientId || 0}`
    const response = await this.api.get<ClientDetailResponse>(url, {
      params: { workspace_id: workspaceId, ...params }
    })
    return this.handleResponse(response)
  }

  async getMemberPerformance(
    memberId: number,
    workspaceId: number,
    params: {
      period?: string
      start_date?: string
      end_date?: string
    } = {}
  ): Promise<MemberPerformanceResponse> {
    const response = await this.api.get<MemberPerformanceResponse>(`/reports/member/${memberId}`, {
      params: { workspace_id: workspaceId, ...params }
    })
    return this.handleResponse(response)
  }

  async getDrillDownReport(request: DrillDownRequest): Promise<DrillDownResponse> {
    const response = await this.api.post<DrillDownResponse>('/reports/drill-down', request)
    return this.handleResponse(response)
  }

  async getReportSummary(
    workspaceId: number,
    params: {
      period?: string
      start_date?: string
      end_date?: string
    } = {}
  ): Promise<{
    workspace_id: number
    date_range: { start: string; end: string; description: string }
    totals: { total_hours: number; billable_hours: number; total_entries: number; billable_percentage: number }
    counts: { total_clients: number; total_members: number; clients_with_time: number; members_with_time: number }
    generated_at: string
  }> {
    const response = await this.api.get(`/reports/summary/${workspaceId}`, { params })
    return this.handleResponse(response)
  }

  // Utility endpoints for dropdowns
  async getClientsForReports(workspaceId: number, includeNoClient = true): Promise<{
    workspace_id: number
    clients: Array<{ id: number | null; name: string; toggl_id: number | null }>
    total_count: number
  }> {
    const response = await this.api.get(`/reports/clients/${workspaceId}`, {
      params: { include_no_client: includeNoClient }
    })
    return this.handleResponse(response)
  }

  async getMembersForReports(workspaceId: number): Promise<{
    workspace_id: number
    members: Array<{ id: number; name: string; toggl_id: number; email?: string }>
    total_count: number
  }> {
    const response = await this.api.get(`/reports/members/${workspaceId}`)
    return this.handleResponse(response)
  }

  // Rate Management API
  async createRate(rate: RateCreate): Promise<Rate> {
    const response = await this.api.post<Rate>('/rates/', rate)
    return this.handleResponse(response)
  }

  async updateRate(rateId: number, rate: Partial<RateCreate>): Promise<Rate> {
    const response = await this.api.put<Rate>(`/rates/${rateId}`, rate)
    return this.handleResponse(response)
  }

  async deleteRate(rateId: number): Promise<void> {
    await this.api.delete(`/rates/${rateId}`)
  }

  async getMemberRates(memberId: number): Promise<{
    member_id: number
    member_name: string
    default_rate?: {
      hourly_rate_usd?: number
      hourly_rate_eur?: number
      effective_date?: string
    }
    client_rates: Record<number, {
      client_name: string
      hourly_rate_usd?: number
      hourly_rate_eur?: number
      effective_date: string
    }>
  }> {
    const response = await this.api.get(`/rates/member/${memberId}`)
    return this.handleResponse(response)
  }

  async getClientRates(clientId: number): Promise<Rate[]> {
    const response = await this.api.get<Rate[]>(`/rates/client/${clientId}`)
    return this.handleResponse(response)
  }

  async getWorkspaceRates(workspaceId: number): Promise<{
    workspace_id: number
    rates: Record<number, {
      member_name: string
      default_rate: {
        usd?: number
        eur?: number
        effective_date?: string
      }
      client_rates: Record<number, {
        usd?: number
        eur?: number
        effective_date: string
      }>
    }>
  }> {
    const response = await this.api.get(`/rates/workspace/${workspaceId}`)
    return this.handleResponse(response)
  }

  async calculateEarnings(
    memberId: number,
    data: {
      duration_seconds: number
      currency: 'usd' | 'eur'
      client_id?: number
      work_date?: string
    }
  ): Promise<{
    member_id: number
    duration_seconds: number
    duration_hours: number
    hourly_rate?: number
    earnings?: number
    currency: string
  }> {
    const response = await this.api.post(`/rates/calculate-earnings/${memberId}`, data)
    return this.handleResponse(response)
  }

  // Data Sync API
  async startSync(data: {
    workspace_id: number
    sync_type?: 'clients' | 'projects' | 'members' | 'time_entries' | 'full'
    start_date?: string
    end_date?: string
    time_entries_days?: number
  }): Promise<SyncLog> {
    const response = await this.api.post<SyncLog>('/sync/start', data)
    return this.handleResponse(response)
  }

  async getSyncStatus(workspaceId: number): Promise<SyncStatus> {
    const response = await this.api.get<SyncStatus>(`/sync/status/${workspaceId}`)
    return this.handleResponse(response)
  }

  async getSyncLogs(workspaceId: number, params: {
    sync_type?: string
    limit?: number
  } = {}): Promise<SyncLog[]> {
    const response = await this.api.get<SyncLog[]>(`/sync/logs/${workspaceId}`, { params })
    return this.handleResponse(response)
  }

  async cleanupOldData(workspaceId: number, daysToKeep = 90): Promise<{
    workspace_id: number
    days_to_keep: number
    deleted_records: number
    message: string
  }> {
    const response = await this.api.post(`/sync/cleanup/${workspaceId}`, { days_to_keep: daysToKeep })
    return this.handleResponse(response)
  }

  async testTogglConnection(): Promise<{
    status: string
    user: { id: number; name: string; email: string }
    workspaces: Array<{ id: number; name: string }>
    message: string
  }> {
    const response = await this.api.get('/sync/test/connection')
    return this.handleResponse(response)
  }

  async getSyncSummary(workspaceId: number): Promise<{
    workspace_id: number
    data_counts: {
      clients: number
      projects: number
      members: number
      time_entries: number
    }
    latest_sync_times: Record<string, string | null>
    summary: string
  }> {
    const response = await this.api.get(`/sync/summary/${workspaceId}`)
    return this.handleResponse(response)
  }

  // Test API (for development)
  async testConnection(): Promise<{
    status: string
    user: { id: number; name: string; email: string }
    workspaces: Array<{ id: number; name: string }>
  }> {
    const response = await this.api.get('/test/connection')
    return this.handleResponse(response)
  }

  async testClientReports(workspaceId: number, days = 30): Promise<{
    workspace_id: number
    date_range: { start: string; end: string }
    total_clients: number
    reports: Array<{
      client_id?: number
      client_name: string
      total_hours: number
      billable_hours: number
      members: Array<{
        user_name: string
        total_hours: number
        billable_hours: number
        entry_count: number
      }>
    }>
  }> {
    const response = await this.api.get(`/test/client-reports/${workspaceId}`, { params: { days } })
    return this.handleResponse(response)
  }

  // Health check
  async healthCheck(): Promise<{ status: string; service: string }> {
    const response = await this.api.get('/health')
    return this.handleResponse(response)
  }
}

// Create singleton instance
export const apiService = new ApiService()
export default apiService