import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  Clock, 
  DollarSign, 
  Users, 
  TrendingUp, 
  ExternalLink,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react'
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts'

import LoadingSpinner from '@/components/ui/LoadingSpinner'
import ErrorMessage from '@/components/ui/ErrorMessage'
import DateRangePicker, { DateRange } from '@/components/ui/DateRangePicker'
import ClientCard from '@/components/ClientCard'
import { useDateContext } from '@/contexts/DateContext'
import { apiService } from '@/services/api'
import { WorkspaceReportResponse, ClientReportData } from '@/types/api'
import { formatCurrency, formatHours, formatPercentage } from '@/utils/formatters'

const COLORS = ['#0ea5e9', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

export default function Dashboard() {
  const [workspaceReport, setWorkspaceReport] = useState<WorkspaceReportResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { selectedPeriod, customRange, setDateRange } = useDateContext()

  // Hardcoded workspace ID for demo - in real app this would come from user settings
  const WORKSPACE_ID = 842441

  useEffect(() => {
    loadDashboardData()
  }, [selectedPeriod, customRange])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      setError(null)

      const reportData = await apiService.getWorkspaceReport({
        workspace_id: WORKSPACE_ID,
        period: selectedPeriod as any,
        start_date: customRange?.start_date,
        end_date: customRange?.end_date,
        include_financial: true,
        include_non_billable: true,
        sort_by: 'total_hours',
        sort_order: 'desc'
      })

      setWorkspaceReport(reportData)
    } catch (err: any) {
      console.error('Failed to load dashboard data:', err)
      setError(err.response?.data?.detail || 'Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <LoadingSpinner size="lg" text="Loading dashboard..." />
      </div>
    )
  }

  if (error) {
    return (
      <ErrorMessage 
        title="Dashboard Error"
        message={error}
        onRetry={loadDashboardData}
        className="max-w-2xl mx-auto mt-8"
      />
    )
  }

  if (!workspaceReport) {
    return (
      <ErrorMessage 
        title="No Data Available"
        message="No report data available for the selected period."
        onRetry={loadDashboardData}
        className="max-w-2xl mx-auto mt-8"
      />
    )
  }

  const { totals, client_reports, summary, date_range } = workspaceReport

  const handleDateRangeChange = (period: string, range?: DateRange) => {
    setDateRange(period, range)
  }

  // Prepare chart data
  const topClientsData = client_reports.slice(0, 8).map((client, index) => ({
    name: client.client_name.length > 20 
      ? client.client_name.substring(0, 20) + '...' 
      : client.client_name,
    fullName: client.client_name,
    hours: client.total_hours,
    billable: client.billable_hours,
    earnings: client.total_earnings_usd || 0,
    color: COLORS[index % COLORS.length]
  }))

  const pieData = client_reports.slice(0, 6).map((client, index) => ({
    name: client.client_name,
    value: client.total_hours,
    color: COLORS[index % COLORS.length],
    percentage: Math.round((client.total_hours / totals.total_hours) * 100)
  }))

  return (
    <div className="space-y-6">
      {/* Period Selector */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-lg font-semibold text-primary">
            {date_range.description || 'Custom Period'}
          </h2>
          <p className="text-sm text-muted">
            {date_range.start} to {date_range.end}
          </p>
        </div>
        
        <DateRangePicker
          value={selectedPeriod}
          onChange={handleDateRangeChange}
          className="w-auto"
        />
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Hours */}
        <div className="card">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-secondary">Total Hours</p>
                <p className="text-2xl font-bold text-primary">
                  {formatHours(totals.total_hours)}
                </p>
                <p className="text-sm text-muted">
                  All hours are billable
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100 dark:bg-primary-900/30">
                <Clock className="h-6 w-6 text-primary-600 dark:text-primary-400" />
              </div>
            </div>
            <div className="mt-4">
              <div className="flex items-center text-sm">
                <span className="text-secondary">Billable Rate:</span>
                <span className="ml-2 font-medium text-primary">
                  {formatPercentage(totals.billable_percentage || 0)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Total Earnings */}
        <div className="card">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-secondary">Total Earnings</p>
                <p className="text-2xl font-bold text-primary">
                  {formatCurrency(totals.total_earnings_usd || 0, 'USD')}
                </p>
                <p className="text-sm text-muted">
                  All earnings are billable
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-success-100 dark:bg-success-900/30">
                <DollarSign className="h-6 w-6 text-success-600 dark:text-success-400" />
              </div>
            </div>
            <div className="mt-4">
              <div className="flex items-center text-sm">
                <span className="text-secondary">Avg Rate:</span>
                <span className="ml-2 font-medium text-primary">
                  {formatCurrency(totals.average_hourly_rate_usd || 0, 'USD')}/hr
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Active Clients */}
        <div className="card">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-secondary">Active Clients</p>
                <p className="text-2xl font-bold text-primary">
                  {summary.clients_with_time}
                </p>
                <p className="text-sm text-muted">
                  of {summary.total_clients} total
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-warning-100 dark:bg-warning-900/30">
                <Users className="h-6 w-6 text-warning-600 dark:text-warning-400" />
              </div>
            </div>
            <div className="mt-4">
              <div className="flex items-center text-sm">
                <span className="text-secondary">Coverage:</span>
                <span className="ml-2 font-medium text-primary">
                  {formatPercentage((summary.clients_with_time / summary.total_clients) * 100)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Team Members */}
        <div className="card">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-secondary">Team Members</p>
                <p className="text-2xl font-bold text-primary">
                  {summary.total_members}
                </p>
                <p className="text-sm text-muted">
                  {totals.entry_count} entries
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/30">
                <TrendingUp className="h-6 w-6 text-purple-600 dark:text-purple-400" />
              </div>
            </div>
            <div className="mt-4">
              <div className="flex items-center text-sm">
                <span className="text-secondary">Avg/Member:</span>
                <span className="ml-2 font-medium text-primary">
                  {formatHours(totals.total_hours / summary.total_members)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Client Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {client_reports.map((client, index) => (
          <ClientCard 
            key={client.client_id || 'no-client'} 
            client={client}
            color={COLORS[index % COLORS.length]}
          />
        ))}
      </div>

      {/* Client List */}
      <div className="card">
        <div className="card-header">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-lg font-semibold text-primary">Client Performance</h3>
              <p className="text-sm text-muted">
                Detailed breakdown of all clients with activity
              </p>
            </div>
            <Link 
              to="/admin"
              className="btn btn-outline btn-sm"
            >
              Manage Rates
              <ExternalLink className="h-4 w-4 ml-1" />
            </Link>
          </div>
        </div>
        <div className="card-body p-0">
          <div className="overflow-x-auto">
            <table className="table">
              <thead className="table-header">
                <tr>
                  <th className="table-header-cell">Client</th>
                  <th className="table-header-cell">Total Hours</th>
                  <th className="table-header-cell">Billable Hours</th>
                  <th className="table-header-cell">Billable %</th>
                  <th className="table-header-cell">Earnings (USD)</th>
                  <th className="table-header-cell">Members</th>
                  <th className="table-header-cell">Projects</th>
                  <th className="table-header-cell"></th>
                </tr>
              </thead>
              <tbody className="table-body">
                {client_reports.map((client) => (
                  <tr key={client.client_id || 'no-client'} className="table-row">
                    <td className="table-cell">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-8 w-8">
                          <div className="h-8 w-8 rounded-full bg-primary-100 flex items-center justify-center">
                            <span className="text-sm font-medium text-primary-700">
                              {client.client_name.charAt(0).toUpperCase()}
                            </span>
                          </div>
                        </div>
                        <div className="ml-3">
                          <div className="text-sm font-medium text-primary">
                            {client.client_name}
                          </div>
                          <div className="text-sm text-muted">
                            {client.member_reports.length} team member{client.member_reports.length !== 1 ? 's' : ''}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="table-cell">
                      <span className="text-sm font-medium text-primary">
                        {formatHours(client.total_hours)}
                      </span>
                    </td>
                    <td className="table-cell">
                      <span className="text-sm font-medium text-primary">
                        {formatHours(client.billable_hours)}
                      </span>
                    </td>
                    <td className="table-cell">
                      <div className="flex items-center">
                        <div className="flex items-center space-x-1">
                          <span className="text-sm font-medium text-primary">
                            {formatPercentage(client.billable_percentage || 0)}
                          </span>
                          {(client.billable_percentage || 0) >= 80 ? (
                            <ArrowUpRight className="h-4 w-4 text-success-500" />
                          ) : (
                            <ArrowDownRight className="h-4 w-4 text-warning-500" />
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="table-cell">
                      <div className="text-sm">
                        <div className="font-medium text-primary">
                          {formatCurrency(client.total_earnings_usd || 0, 'USD')}
                        </div>
                        <div className="text-muted">
                          All earnings billable
                        </div>
                      </div>
                    </td>
                    <td className="table-cell">
                      <span className="badge badge-secondary">
                        {client.member_reports.length}
                      </span>
                    </td>
                    <td className="table-cell">
                      <span className="badge badge-primary">
                        {client.project_count}
                      </span>
                    </td>
                    <td className="table-cell">
                      <Link 
                        to={`/client/${client.client_id || 0}`}
                        className="btn btn-ghost btn-sm"
                      >
                        View Details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}