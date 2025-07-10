import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Users, Clock, DollarSign, TrendingUp } from 'lucide-react'

import LoadingSpinner from '@/components/ui/LoadingSpinner'
import ErrorMessage from '@/components/ui/ErrorMessage'
import { apiService } from '@/services/api'
import { ClientDetailResponse } from '@/types/api'
import { formatCurrency, formatHours, formatPercentage } from '@/utils/formatters'

export default function ClientDetail() {
  const { clientId } = useParams<{ clientId: string }>()
  const [clientReport, setClientReport] = useState<ClientDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Hardcoded workspace ID for demo
  const WORKSPACE_ID = 123456

  useEffect(() => {
    if (clientId) {
      loadClientReport()
    }
  }, [clientId])

  const loadClientReport = async () => {
    try {
      setLoading(true)
      setError(null)

      const reportData = await apiService.getClientDetail(
        clientId === '0' ? null : parseInt(clientId!),
        WORKSPACE_ID,
        {
          period: 'last_30_days',
          include_project_breakdown: true
        }
      )

      setClientReport(reportData)
    } catch (err: any) {
      console.error('Failed to load client report:', err)
      setError(err.response?.data?.detail || 'Failed to load client report')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <LoadingSpinner size="lg" text="Loading client report..." />
      </div>
    )
  }

  if (error) {
    return (
      <ErrorMessage 
        title="Client Report Error"
        message={error}
        onRetry={loadClientReport}
        className="max-w-2xl mx-auto mt-8"
      />
    )
  }

  if (!clientReport) {
    return (
      <ErrorMessage 
        title="No Data Available"
        message="No report data available for this client."
        className="max-w-2xl mx-auto mt-8"
      />
    )
  }

  const { totals, projects, date_range } = clientReport

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/" className="btn btn-ghost btn-sm">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Dashboard
          </Link>
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">
              {clientReport.client_name}
            </h1>
            <p className="text-sm text-gray-500">
              {date_range.description} • {projects.length} project{projects.length !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Hours</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatHours(totals.total_hours)}
                </p>
                <p className="text-sm text-gray-500">
                  {totals.entry_count} entries
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100">
                <Clock className="h-6 w-6 text-primary-600" />
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Billable Hours</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatHours(totals.billable_hours)}
                </p>
                <p className="text-sm text-gray-500">
                  {formatPercentage(totals.billable_percentage || 0)} billable
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-success-100">
                <TrendingUp className="h-6 w-6 text-success-600" />
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Earnings</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatCurrency(totals.total_earnings_usd || 0, 'USD')}
                </p>
                <p className="text-sm text-gray-500">
                  {formatCurrency(totals.total_earnings_eur || 0, 'EUR')}
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-warning-100">
                <DollarSign className="h-6 w-6 text-warning-600" />
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Team Members</p>
                <p className="text-2xl font-bold text-gray-900">
                  {Array.from(new Set(projects.flatMap(p => p.members.map(m => m.member_id)))).length}
                </p>
                <p className="text-sm text-gray-500">
                  across {projects.length} projects
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-purple-100">
                <Users className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Project Breakdown */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold">Project Breakdown</h3>
          <p className="text-sm text-gray-500">
            Time allocation and earnings by project
          </p>
        </div>
        <div className="card-body p-0">
          <div className="space-y-6 p-6">
            {projects.map((project) => (
              <div key={project.project_id || 'no-project'} className="border-l-4 border-primary-500 pl-4">
                {/* Project Header */}
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h4 className="text-lg font-medium text-gray-900">
                      {project.project_name}
                    </h4>
                    <div className="flex items-center space-x-4 text-sm text-gray-500">
                      <span>{formatHours(project.total_hours)} total</span>
                      <span>{formatHours(project.billable_hours)} billable</span>
                      <span>{project.members.length} member{project.members.length !== 1 ? 's' : ''}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-semibold text-gray-900">
                      {formatCurrency(project.total_earnings_usd || 0, 'USD')}
                    </div>
                    <div className="text-sm text-gray-500">
                      {formatCurrency(project.total_earnings_eur || 0, 'EUR')}
                    </div>
                  </div>
                </div>

                {/* Project Members */}
                <div className="overflow-x-auto">
                  <table className="min-w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-2 text-sm font-medium text-gray-600">Member</th>
                        <th className="text-right py-2 text-sm font-medium text-gray-600">Hours</th>
                        <th className="text-right py-2 text-sm font-medium text-gray-600">Billable</th>
                        <th className="text-right py-2 text-sm font-medium text-gray-600">Rate (USD)</th>
                        <th className="text-right py-2 text-sm font-medium text-gray-600">Earnings</th>
                      </tr>
                    </thead>
                    <tbody>
                      {project.members.map((member) => (
                        <tr key={member.member_id} className="border-b border-gray-100">
                          <td className="py-2">
                            <Link 
                              to={`/member/${member.member_id}`}
                              className="text-sm font-medium text-primary-600 hover:text-primary-700"
                            >
                              {member.member_name}
                            </Link>
                          </td>
                          <td className="text-right py-2 text-sm text-gray-900">
                            {formatHours(member.total_hours)}
                          </td>
                          <td className="text-right py-2 text-sm text-gray-900">
                            {formatHours(member.billable_hours)}
                          </td>
                          <td className="text-right py-2 text-sm text-money">
                            {member.hourly_rate_usd 
                              ? formatCurrency(member.hourly_rate_usd, 'USD')
                              : '-'
                            }
                          </td>
                          <td className="text-right py-2">
                            <div className="text-sm font-medium text-gray-900">
                              {formatCurrency(member.total_earnings_usd || 0, 'USD')}
                            </div>
                            <div className="text-xs text-gray-500">
                              {formatCurrency(member.billable_earnings_usd || 0, 'USD')} billable
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}

            {projects.length === 0 && (
              <div className="text-center py-8">
                <p className="text-gray-500">No project data available for this period.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Summary Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold">Performance Metrics</h3>
          </div>
          <div className="card-body space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Billable Rate</span>
              <span className="text-lg font-semibold text-gray-900">
                {formatPercentage(totals.billable_percentage || 0)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Average Hourly Rate</span>
              <span className="text-lg font-semibold text-money">
                {formatCurrency(totals.average_hourly_rate_usd || 0, 'USD')}/hr
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Entries per Day</span>
              <span className="text-lg font-semibold text-gray-900">
                {(totals.entry_count / 30).toFixed(1)}
              </span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold">Financial Summary</h3>
          </div>
          <div className="card-body space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Total Value (USD)</span>
              <span className="text-lg font-semibold text-success-600">
                {formatCurrency(totals.total_earnings_usd || 0, 'USD')}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Billable Value (USD)</span>
              <span className="text-lg font-semibold text-success-600">
                {formatCurrency(totals.billable_earnings_usd || 0, 'USD')}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Total Value (EUR)</span>
              <span className="text-lg font-semibold text-primary-600">
                {formatCurrency(totals.total_earnings_eur || 0, 'EUR')}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}