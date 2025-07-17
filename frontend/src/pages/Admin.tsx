import { useState, useEffect } from 'react'
import { 
  DollarSign, 
  Users, 
  Plus, 
  Edit, 
  Trash2, 
  Save,
  RefreshCw,
  AlertCircle,
  CheckCircle
} from 'lucide-react'

import LoadingSpinner from '@/components/ui/LoadingSpinner'
import ErrorMessage from '@/components/ui/ErrorMessage'
import { apiService } from '@/services/api'
import { Rate, Member, Client } from '@/types/api'
import { formatCurrency, formatDate } from '@/utils/formatters'

export default function Admin() {
  const [members, setMembers] = useState<Member[]>([])
  const [clients, setClients] = useState<Client[]>([])
  const [workspaceRates, setWorkspaceRates] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingRate, setEditingRate] = useState<{
    memberId: number
    clientId?: number
    isNew: boolean
  } | null>(null)
  const [showClientSelector, setShowClientSelector] = useState<{
    memberId: number
    show: boolean
  } | null>(null)
  const [rateForm, setRateForm] = useState({
    hourly_rate_usd: '',
    hourly_rate_eur: '',
    effective_date: '2024-07-16' // Set to earliest time entry date to cover all data
  })
  const [saving, setSaving] = useState(false)

  // Hardcoded workspace ID for demo
  const WORKSPACE_ID = 842441

  useEffect(() => {
    loadAdminData()
  }, [])

  // Close client selector when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showClientSelector?.show) {
        const target = event.target as HTMLElement
        if (!target.closest('.relative')) {
          setShowClientSelector(null)
        }
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showClientSelector])

  const loadAdminData = async () => {
    try {
      setLoading(true)
      setError(null)

      const [membersData, clientsData, ratesData] = await Promise.all([
        apiService.getMembersForReports(WORKSPACE_ID),
        apiService.getClientsForReports(WORKSPACE_ID, false), // Don't include "No Client"
        apiService.getWorkspaceRates(WORKSPACE_ID)
      ])

      setMembers(membersData.members)
      setClients(clientsData.clients.filter(c => c.id !== null))
      setWorkspaceRates(ratesData)
    } catch (err: any) {
      console.error('Failed to load admin data:', err)
      setError(err.response?.data?.detail || 'Failed to load admin data')
    } finally {
      setLoading(false)
    }
  }

  const handleEditRate = (memberId: number, clientId?: number) => {
    const memberRates = workspaceRates?.rates[memberId]
    
    let currentRate = null
    if (clientId) {
      currentRate = memberRates?.client_rates[clientId]
    } else {
      currentRate = memberRates?.default_rate
    }

    setEditingRate({ memberId, clientId, isNew: !currentRate })
    setRateForm({
      hourly_rate_usd: currentRate?.usd?.toString() || '',
      hourly_rate_eur: currentRate?.eur?.toString() || '',
      effective_date: '2024-07-16' // Always use earliest date to cover all historical data
    })
  }

  const handleSaveRate = async () => {
    if (!editingRate) return

    try {
      setSaving(true)
      
      const rateData = {
        member_id: editingRate.memberId,
        client_id: editingRate.clientId || undefined,
        hourly_rate_usd: rateForm.hourly_rate_usd ? parseFloat(rateForm.hourly_rate_usd) : undefined,
        hourly_rate_eur: rateForm.hourly_rate_eur ? parseFloat(rateForm.hourly_rate_eur) : undefined,
        effective_date: rateForm.effective_date
      }

      await apiService.createRate(rateData)
      await loadAdminData() // Reload data
      
      setEditingRate(null)
      setRateForm({
        hourly_rate_usd: '',
        hourly_rate_eur: '',
        effective_date: '2024-07-16' // Always use earliest date to cover all historical data
      })
    } catch (err: any) {
      console.error('Failed to save rate:', err)
      setError(err.response?.data?.detail || 'Failed to save rate')
    } finally {
      setSaving(false)
    }
  }

  const handleCancelEdit = () => {
    setEditingRate(null)
    setShowClientSelector(null)
    setRateForm({
      hourly_rate_usd: '',
      hourly_rate_eur: '',
      effective_date: '2024-07-16' // Always use earliest date to cover all historical data
    })
  }

  const handleAddClientRate = (memberId: number) => {
    setShowClientSelector({ memberId, show: true })
  }

  const handleSelectClient = (memberId: number, clientId: number) => {
    setShowClientSelector(null)
    handleEditRate(memberId, clientId)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <LoadingSpinner size="lg" text="Loading admin panel..." />
      </div>
    )
  }

  if (error) {
    return (
      <ErrorMessage 
        title="Admin Panel Error"
        message={error}
        onRetry={loadAdminData}
        className="max-w-2xl mx-auto mt-8"
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Rate Management</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Manage hourly rates for team members and clients
          </p>
        </div>
        <button 
          onClick={loadAdminData}
          className="btn btn-outline btn-sm"
          disabled={loading}
        >
          <RefreshCw className="h-4 w-4 mr-1" />
          Refresh
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Team Members</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{members.length}</p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100">
                <Users className="h-6 w-6 text-primary-600" />
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Active Clients</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{clients.length}</p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-success-100">
                <DollarSign className="h-6 w-6 text-success-600" />
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Rate Configurations</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {workspaceRates ? Object.keys(workspaceRates.rates).length : 0}
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-warning-100">
                <Edit className="h-6 w-6 text-warning-600" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Rate Management Table */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold">Member Rates</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Set default rates and client-specific overrides for each team member
          </p>
        </div>
        <div className="card-body p-0">
          <div className="overflow-x-auto">
            <table className="table">
              <thead className="table-header">
                <tr>
                  <th className="table-header-cell">Member</th>
                  <th className="table-header-cell">Default Rate (USD)</th>
                  <th className="table-header-cell">Default Rate (EUR)</th>
                  <th className="table-header-cell">Client Overrides</th>
                  <th className="table-header-cell">Actions</th>
                </tr>
              </thead>
              <tbody className="table-body">
                {members.map((member) => {
                  const memberRates = workspaceRates?.rates[member.id]
                  const defaultRate = memberRates?.default_rate
                  const clientRates = memberRates?.client_rates || {}
                  
                  return (
                    <tr key={member.id} className="table-row">
                      <td className="table-cell">
                        <div>
                          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {member.name}
                          </div>
                          <div className="text-sm text-gray-500 dark:text-gray-400">
                            {member.email}
                          </div>
                        </div>
                      </td>
                      <td className="table-cell">
                        {editingRate?.memberId === member.id && !editingRate.clientId ? (
                          <input
                            type="number"
                            value={rateForm.hourly_rate_usd}
                            onChange={(e) => setRateForm(prev => ({ ...prev, hourly_rate_usd: e.target.value }))}
                            className="form-input w-24"
                            placeholder="0.00"
                            step="0.01"
                          />
                        ) : (
                          <span className="text-sm font-medium text-money">
                            {defaultRate?.usd ? formatCurrency(defaultRate.usd, 'USD') : '-'}
                          </span>
                        )}
                      </td>
                      <td className="table-cell">
                        {editingRate?.memberId === member.id && !editingRate.clientId ? (
                          <input
                            type="number"
                            value={rateForm.hourly_rate_eur}
                            onChange={(e) => setRateForm(prev => ({ ...prev, hourly_rate_eur: e.target.value }))}
                            className="form-input w-24"
                            placeholder="0.00"
                            step="0.01"
                          />
                        ) : (
                          <span className="text-sm font-medium text-money">
                            {defaultRate?.eur ? formatCurrency(defaultRate.eur, 'EUR') : '-'}
                          </span>
                        )}
                      </td>
                      <td className="table-cell">
                        <div className="space-y-1">
                          {Object.entries(clientRates).map(([clientId, rate]: [string, any]) => {
                            const client = clients.find(c => c.id === parseInt(clientId))
                            return (
                              <div key={clientId} className="flex items-center justify-between text-xs bg-gray-50 dark:bg-gray-800 p-2 rounded">
                                <span className="text-gray-600 dark:text-gray-300 font-medium">{client?.name || 'Unknown'}</span>
                                <div className="flex items-center space-x-2">
                                  <div className="flex space-x-1">
                                    {rate.usd && (
                                      <span className="text-money font-medium">{formatCurrency(rate.usd, 'USD')}</span>
                                    )}
                                    {rate.eur && (
                                      <span className="text-money font-medium">{formatCurrency(rate.eur, 'EUR')}</span>
                                    )}
                                  </div>
                                  <button
                                    onClick={() => handleEditRate(member.id, parseInt(clientId))}
                                    className="btn btn-ghost btn-sm p-1"
                                    title="Edit client rate"
                                  >
                                    <Edit className="h-3 w-3" />
                                  </button>
                                </div>
                              </div>
                            )
                          })}
                          {Object.keys(clientRates).length === 0 && (
                            <span className="text-xs text-gray-400 dark:text-gray-500">No overrides</span>
                          )}
                        </div>
                      </td>
                      <td className="table-cell">
                        {editingRate?.memberId === member.id && !editingRate.clientId ? (
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={handleSaveRate}
                              disabled={saving}
                              className="btn btn-success btn-sm"
                            >
                              <Save className="h-4 w-4" />
                            </button>
                            <button
                              onClick={handleCancelEdit}
                              className="btn btn-outline btn-sm"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => handleEditRate(member.id)}
                              className="btn btn-ghost btn-sm"
                              title="Edit default rate"
                            >
                              <Edit className="h-4 w-4" />
                            </button>
                            <div className="relative">
                              <button
                                onClick={() => handleAddClientRate(member.id)}
                                className="btn btn-ghost btn-sm"
                                title="Add client override"
                              >
                                <Plus className="h-4 w-4" />
                              </button>
                              {showClientSelector?.memberId === member.id && showClientSelector.show && (
                                <div className="absolute right-0 top-8 z-10 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg py-1 min-w-48">
                                  <div className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-600">
                                    Select Client
                                  </div>
                                  {clients.filter(client => {
                                    // Only show clients that don't already have a rate for this member
                                    const memberRates = workspaceRates?.rates[member.id]
                                    return !memberRates?.client_rates[client.id]
                                  }).map((client) => (
                                    <button
                                      key={client.id}
                                      onClick={() => handleSelectClient(member.id, client.id)}
                                      className="block w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                                    >
                                      {client.name}
                                    </button>
                                  ))}
                                  {clients.filter(client => {
                                    const memberRates = workspaceRates?.rates[member.id]
                                    return !memberRates?.client_rates[client.id]
                                  }).length === 0 && (
                                    <div className="px-3 py-2 text-xs text-gray-400 dark:text-gray-500">
                                      All clients have rates
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>


      {/* Instructions */}
      <div className="card bg-blue-50 border-blue-200">
        <div className="card-body">
          <div className="flex items-start space-x-3">
            <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5" />
            <div>
              <h4 className="text-sm font-medium text-blue-900">Rate Management Tips</h4>
              <ul className="mt-2 text-sm text-blue-800 space-y-1">
                <li>• Default rates apply to all clients unless overridden</li>
                <li>• Client-specific rates take precedence over default rates</li>
                <li>• Rates are applied based on the effective date</li>
                <li>• Both USD and EUR rates are optional but recommended</li>
                <li>• Changes take effect immediately for new time entries</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}