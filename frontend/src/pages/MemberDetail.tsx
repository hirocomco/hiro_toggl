import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Clock, DollarSign, TrendingUp, Target } from 'lucide-react'

import LoadingSpinner from '@/components/ui/LoadingSpinner'
import ErrorMessage from '@/components/ui/ErrorMessage'
import { apiService } from '@/services/api'
import { MemberPerformanceResponse } from '@/types/api'
import { formatCurrency, formatHours, formatPercentage } from '@/utils/formatters'

export default function MemberDetail() {
  const { memberId } = useParams<{ memberId: string }>()
  const [memberReport, setMemberReport] = useState<MemberPerformanceResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Hardcoded workspace ID for demo
  const WORKSPACE_ID = 123456

  useEffect(() => {
    if (memberId) {
      loadMemberReport()
    }
  }, [memberId])

  const loadMemberReport = async () => {
    try {
      setLoading(true)
      setError(null)

      const reportData = await apiService.getMemberPerformance(
        parseInt(memberId!),
        WORKSPACE_ID,
        {
          period: 'last_30_days'
        }
      )

      setMemberReport(reportData)
    } catch (err: any) {
      console.error('Failed to load member report:', err)
      setError(err.response?.data?.detail || 'Failed to load member report')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <LoadingSpinner size="lg" text="Loading member report..." />
      </div>
    )
  }

  if (error) {
    return (
      <ErrorMessage 
        title="Member Report Error"
        message={error}
        onRetry={loadMemberReport}
        className="max-w-2xl mx-auto mt-8"
      />
    )
  }

  if (!memberReport) {
    return (
      <ErrorMessage 
        title="No Data Available"
        message="No report data available for this member."
        className="max-w-2xl mx-auto mt-8"
      />
    )
  }

  const { totals, clients, date_range } = memberReport

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
              {memberReport.member_name}
            </h1>
            <p className="text-sm text-gray-500">
              {date_range.description} • {totals.client_count} client{totals.client_count !== 1 ? 's' : ''}
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
                  {formatPercentage(totals.billable_percentage || 0)} rate
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-success-100">
                <Target className="h-6 w-6 text-success-600" />
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
                <p className="text-sm text-gray-600">Avg Hourly Rate</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatCurrency(totals.average_hourly_rate_usd || 0, 'USD')}
                </p>
                <p className="text-sm text-gray-500">
                  per hour
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-purple-100">
                <TrendingUp className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Client Breakdown */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold">Client Performance</h3>
          <p className="text-sm text-gray-500">
            Time allocation and earnings by client
          </p>
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
                  <th className="table-header-cell">Hourly Rate (USD)</th>
                  <th className="table-header-cell">Total Earnings</th>
                  <th className="table-header-cell">Entries</th>
                </tr>
              </thead>
              <tbody className="table-body">
                {clients.map((client) => (
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
                          <Link 
                            to={`/client/${client.client_id || 0}`}
                            className="text-sm font-medium text-primary-600 hover:text-primary-700"
                          >
                            {client.client_name}
                          </Link>
                        </div>
                      </div>
                    </td>
                    <td className="table-cell">
                      <span className="text-sm font-medium">
                        {formatHours(client.total_hours)}
                      </span>
                    </td>
                    <td className="table-cell">
                      <span className="text-sm font-medium">
                        {formatHours(client.billable_hours)}
                      </span>
                    </td>
                    <td className="table-cell">
                      <div className="flex items-center">
                        <span className="text-sm font-medium">
                          {formatPercentage(
                            client.total_hours > 0 
                              ? (client.billable_hours / client.total_hours) * 100 
                              : 0
                          )}
                        </span>
                      </div>
                    </td>
                    <td className="table-cell">
                      <span className="text-sm font-medium text-money">
                        {client.hourly_rate_usd 
                          ? formatCurrency(client.hourly_rate_usd, 'USD')
                          : '-'
                        }
                      </span>
                    </td>
                    <td className="table-cell">
                      <div className="text-sm">
                        <div className="font-medium text-gray-900">
                          {formatCurrency(client.total_earnings_usd || 0, 'USD')}
                        </div>
                        <div className="text-gray-500">
                          {formatCurrency(client.billable_earnings_usd || 0, 'USD')} billable
                        </div>
                      </div>
                    </td>
                    <td className="table-cell">
                      <span className="badge badge-secondary">
                        {client.entry_count}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {clients.length === 0 && (
            <div className="text-center py-8">
              <p className="text-gray-500">No client data available for this period.</p>
            </div>
          )}
        </div>
      </div>

      {/* Performance Insights */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold">Performance Metrics</h3>
          </div>
          <div className="card-body space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Overall Billable Rate</span>
              <span className="text-lg font-semibold text-gray-900">
                {formatPercentage(totals.billable_percentage || 0)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Hours per Day</span>
              <span className="text-lg font-semibold text-gray-900">
                {(totals.total_hours / 30).toFixed(1)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Entries per Day</span>
              <span className="text-lg font-semibold text-gray-900">
                {(totals.entry_count / 30).toFixed(1)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Client Diversity</span>
              <span className="text-lg font-semibold text-gray-900">
                {totals.client_count} client{totals.client_count !== 1 ? 's' : ''}
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
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Daily Average</span>
              <span className="text-lg font-semibold text-gray-900">
                {formatCurrency((totals.total_earnings_usd || 0) / 30, 'USD')}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Top Clients by Hours */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold">Time Distribution</h3>
          <p className="text-sm text-gray-500">
            Where time was spent during this period
          </p>
        </div>
        <div className="card-body">
          <div className="space-y-3">
            {clients
              .sort((a, b) => b.total_hours - a.total_hours)
              .slice(0, 5)
              .map((client) => {
                const percentage = (client.total_hours / totals.total_hours) * 100
                return (
                  <div key={client.client_id || 'no-client'} className="flex items-center">
                    <div className="flex-1">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="font-medium text-gray-900">{client.client_name}</span>
                        <span className="text-gray-500">
                          {formatHours(client.total_hours)} ({formatPercentage(percentage)})
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-primary-500 h-2 rounded-full"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  </div>
                )
              })}
          </div>
        </div>
      </div>
    </div>
  )
}