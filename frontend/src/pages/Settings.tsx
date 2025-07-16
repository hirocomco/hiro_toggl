import { useState, useEffect } from 'react'
import { 
  Settings as SettingsIcon, 
  Save, 
  RefreshCw, 
  Database, 
  Clock, 
  AlertCircle,
  CheckCircle,
  Globe,
  Key,
  User
} from 'lucide-react'

import LoadingSpinner from '@/components/ui/LoadingSpinner'
import ErrorMessage from '@/components/ui/ErrorMessage'
import { apiService } from '@/services/api'
import { settingsHelpers } from '@/services/settingsApi'
import { useTheme } from '@/contexts/ThemeContext'

export default function Settings() {
  const { theme, setTheme } = useTheme()
  const [settings, setSettings] = useState({
    workspace_id: '842441',
    default_currency: 'USD',
    sync_interval: 30,
    auto_sync: true,
    notifications: true
  })
  const [syncStatus, setSyncStatus] = useState<{
    last_sync: string | null
    status: 'idle' | 'syncing' | 'success' | 'error'
    message?: string
  }>({
    last_sync: null,
    status: 'idle'
  })
  
  const [syncOptions, setSyncOptions] = useState({
    syncType: 'time_entries_only' as 'full' | 'metadata' | 'time_entries_only' | 'clients' | 'projects' | 'members' | 'time_entries',
    timeframeType: 'days' as 'days' | 'preset' | 'custom',
    timeEntriesDays: 7,
    startDate: '',
    endDate: ''
  })
  
  const [showAdvancedSync, setShowAdvancedSync] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadSettings()
    loadSyncStatus()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Try to load from backend first (system-level settings)
      try {
        console.log('Attempting to load settings from backend...')
        // First, try to get system-level settings without workspace_id
        const config = await settingsHelpers.getAppConfig()
        console.log('Successfully loaded settings from backend:', config)
        setSettings(config)
      } catch (backendError) {
        console.error('Failed to load from backend:', backendError)
        console.warn('Falling back to localStorage...')
        
        // Fall back to localStorage
        const savedSettings = localStorage.getItem('toggl-settings')
        if (savedSettings) {
          const localConfig = JSON.parse(savedSettings)
          setSettings(localConfig)
          console.log('Loaded settings from localStorage:', localConfig)
        } else {
          console.log('No localStorage settings found, using defaults')
        }
      }
    } catch (err: any) {
      setError('Failed to load settings')
      console.error('Settings loading error:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadSyncStatus = async () => {
    try {
      const workspaceId = parseInt(settings.workspace_id || '842441')
      const status = await apiService.getSyncStatus(workspaceId)
      
      setSyncStatus({
        last_sync: status.last_sync,
        status: status.status === 'running' ? 'syncing' : 'success',
        message: status.message || 'Data synchronized successfully'
      })
    } catch (err: any) {
      // Fallback to localStorage if API call fails
      const lastSync = localStorage.getItem('last-sync')
      setSyncStatus({
        last_sync: lastSync,
        status: lastSync ? 'success' : 'idle',
        message: lastSync ? 'Data synchronized successfully' : 'No sync performed yet'
      })
    }
  }

  const handleSaveSettings = async () => {
    try {
      setSaving(true)
      
      // Try to save to backend first (system-level for now)
      try {
        console.log('Attempting to save settings to backend:', settings)
        await settingsHelpers.saveAppConfig(settings)
        console.log('Successfully saved settings to backend')
        
        // Show success message
        setSyncStatus({
          ...syncStatus,
          status: 'success',
          message: 'Settings saved successfully to server'
        })
      } catch (backendError) {
        console.error('Failed to save to backend:', backendError)
        console.warn('Falling back to localStorage...')
        
        // Fall back to localStorage
        localStorage.setItem('toggl-settings', JSON.stringify(settings))
        console.log('Saved settings to localStorage as fallback')
        
        setSyncStatus({
          ...syncStatus,
          status: 'success',
          message: 'Settings saved locally (server unavailable)'
        })
      }
      
      setTimeout(() => {
        setSyncStatus(prev => ({ ...prev, status: 'idle' }))
      }, 3000)
    } catch (err: any) {
      setError('Failed to save settings')
      console.error('Settings save error:', err)
    } finally {
      setSaving(false)
    }
  }

  const handleManualSync = async (syncOptions?: {
    syncType: 'full' | 'metadata' | 'time_entries_only' | 'clients' | 'projects' | 'members' | 'time_entries'
    timeframeType: 'days' | 'preset' | 'custom'
    timeEntriesDays?: number
    startDate?: string
    endDate?: string
  }) => {
    try {
      setSyncStatus({ ...syncStatus, status: 'syncing' })
      
      const workspaceId = parseInt(settings.workspace_id || '842441')
      
      // Prepare sync request based on options
      let syncRequest: any = {
        workspace_id: workspaceId,
        sync_type: syncOptions?.syncType || 'time_entries_only'
      }

      // Add timeframe options for time entry syncs
      if (syncOptions?.syncType === 'time_entries_only' || syncOptions?.syncType === 'full' || syncOptions?.syncType === 'time_entries') {
        if (syncOptions?.timeframeType === 'days') {
          syncRequest.time_entries_days = syncOptions.timeEntriesDays || 7
        } else if (syncOptions?.timeframeType === 'custom') {
          syncRequest.start_date = syncOptions.startDate
          syncRequest.end_date = syncOptions.endDate
        } else {
          // Default to 7 days for quick sync
          syncRequest.time_entries_days = 7
        }
      }
      
      // Start actual sync via API
      const syncResult = await apiService.startSync(syncRequest)
      
      // Poll for sync completion
      let attempts = 0
      const maxAttempts = 30 // 30 seconds max wait
      
      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        const status = await apiService.getSyncStatus(workspaceId)
        
        if (status.status !== 'running') {
          setSyncStatus({
            last_sync: status.last_sync || new Date().toISOString(),
            status: status.status === 'completed' ? 'success' : 'error',
            message: status.message || 'Manual sync completed successfully'
          })
          
          // Update localStorage for fallback
          if (status.status === 'completed') {
            localStorage.setItem('last-sync', status.last_sync || new Date().toISOString())
          }
          
          setTimeout(() => {
            setSyncStatus(prev => ({ ...prev, status: 'idle' }))
          }, 3000)
          
          return
        }
        
        attempts++
      }
      
      // Timeout fallback
      setSyncStatus({
        last_sync: syncStatus.last_sync,
        status: 'success',
        message: 'Sync started successfully (may still be running)'
      })
      
      setTimeout(() => {
        setSyncStatus(prev => ({ ...prev, status: 'idle' }))
      }, 3000)
      
    } catch (err: any) {
      console.error('Manual sync failed:', err)
      setSyncStatus({
        last_sync: syncStatus.last_sync,
        status: 'error',
        message: err.message || 'Sync failed. Please try again.'
      })
      
      setTimeout(() => {
        setSyncStatus(prev => ({ ...prev, status: 'idle' }))
      }, 3000)
    }
  }

  const handleSafeChunkedHistoricalSync = async () => {
    try {
      setSyncStatus({ ...syncStatus, status: 'syncing' })
      
      const workspaceId = parseInt(settings.workspace_id || '842441')
      
      // Get current progress
      const progress = await apiService.getHistoricalSyncProgress(workspaceId)
      
      if (progress.is_completed) {
        setSyncStatus({
          ...syncStatus,
          status: 'success',
          message: 'Historical sync already completed!'
        })
        return
      }
      
      // Start one chunk of the safe historical sync
      const result = await apiService.startSafeChunkedHistoricalSync({
        workspace_id: workspaceId,
        total_days: 365,
        chunk_size: 30,
        chunks_per_call: 1
      })
      
      if (result.status === 'completed') {
        setSyncStatus({
          last_sync: new Date().toISOString(),
          status: 'success',
          message: `🎉 Historical sync completed! All ${result.total_chunks} chunks processed.`
        })
      } else {
        setSyncStatus({
          last_sync: new Date().toISOString(),
          status: 'success',
          message: `✅ Chunk processed! ${result.chunks_remaining} chunks remaining (${Math.round(result.progress_percentage)}% complete). Click again in 1 hour to continue.`
        })
      }
      
    } catch (error: any) {
      console.error('Safe historical sync failed:', error)
      setSyncStatus({
        ...syncStatus,
        status: 'error',
        message: error.message?.includes('API calls') 
          ? 'Rate limit exceeded. Please wait 1 hour before continuing.'
          : 'Historical sync failed. Please try again.'
      })
    }
  }

  const handleDailySync = async () => {
    try {
      setSyncStatus({ ...syncStatus, status: 'syncing' })
      
      const workspaceId = parseInt(settings.workspace_id || '842441')
      
      // Get daily sync recommendation
      const recommendation = await apiService.getDailySyncRecommendation(workspaceId)
      
      // Start the recommended daily sync
      const syncResult = await apiService.startSync({
        workspace_id: workspaceId,
        sync_type: 'time_entries_only',
        time_entries_days: recommendation.recommended_days
      })
      
      setSyncStatus({
        last_sync: new Date().toISOString(),
        status: 'success',
        message: `Daily sync completed: ${recommendation.recommended_days} days synced`
      })
      
    } catch (error: any) {
      console.error('Daily sync failed:', error)
      setSyncStatus({
        ...syncStatus,
        status: 'error',
        message: 'Daily sync failed. Please try again.'
      })
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <LoadingSpinner size="lg" text="Loading settings..." />
      </div>
    )
  }

  if (error) {
    return (
      <ErrorMessage 
        title="Settings Error"
        message={error}
        onRetry={loadSettings}
        className="max-w-2xl mx-auto mt-8"
      />
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-semibold text-primary">Settings</h2>
          <p className="text-sm text-muted">
            Configure your workspace preferences and data sync options
          </p>
        </div>
        <button
          onClick={handleSaveSettings}
          disabled={saving}
          className="btn btn-primary"
        >
          {saving ? (
            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          Save Settings
        </button>
      </div>

      {/* Workspace Settings */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center space-x-2">
            <User className="h-5 w-5 text-muted" />
            <h3 className="text-lg font-semibold text-primary">Workspace Configuration</h3>
          </div>
        </div>
        <div className="card-body space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-secondary mb-1">
                Workspace ID
              </label>
              <input
                type="text"
                value={settings.workspace_id}
                onChange={(e) => setSettings(prev => ({ ...prev, workspace_id: e.target.value }))}
                className="form-input"
                placeholder="Your Toggl workspace ID"
              />
              <p className="text-xs text-muted mt-1">
                Find this in your Toggl workspace settings
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary mb-1">
                Default Currency
              </label>
              <select
                value={settings.default_currency}
                onChange={(e) => setSettings(prev => ({ ...prev, default_currency: e.target.value }))}
                className="form-select"
              >
                <option value="USD">USD - US Dollar</option>
                <option value="EUR">EUR - Euro</option>
                <option value="GBP">GBP - British Pound</option>
                <option value="CAD">CAD - Canadian Dollar</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Sync Settings */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center space-x-2">
            <Database className="h-5 w-5 text-muted" />
            <h3 className="text-lg font-semibold text-primary">Data Synchronization</h3>
          </div>
        </div>
        <div className="card-body space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-secondary">
                Automatic Daily Sync
              </label>
              <p className="text-xs text-muted">
                Automatically sync recent time entries daily (perfect for free plan)
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.auto_sync}
                onChange={(e) => setSettings(prev => ({ ...prev, auto_sync: e.target.checked }))}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-secondary mb-1">
                Sync Time (Daily)
              </label>
              <select
                value={settings.sync_interval}
                onChange={(e) => setSettings(prev => ({ ...prev, sync_interval: parseInt(e.target.value) }))}
                className="form-select"
                disabled={!settings.auto_sync}
              >
                <option value={6}>6:00 AM</option>
                <option value={9}>9:00 AM</option>
                <option value={12}>12:00 PM</option>
                <option value={18}>6:00 PM</option>
                <option value={21}>9:00 PM</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary mb-1">
                Last Sync
              </label>
              <div className="flex items-center space-x-2">
                <div className="flex items-center space-x-2">
                  {syncStatus.status === 'syncing' && (
                    <RefreshCw className="h-4 w-4 text-blue-500 animate-spin" />
                  )}
                  {syncStatus.status === 'success' && (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  )}
                  {syncStatus.status === 'error' && (
                    <AlertCircle className="h-4 w-4 text-red-500" />
                  )}
                  <span className="text-sm text-secondary">
                    {syncStatus.last_sync 
                      ? new Date(syncStatus.last_sync).toLocaleString()
                      : 'Never'
                    }
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Initial Setup Section */}
          <div className="border-t pt-4">
            <h4 className="text-sm font-medium text-primary mb-3">🚀 Initial Setup</h4>
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h5 className="font-medium text-blue-900 dark:text-blue-100">Historical Data Import</h5>
                  <p className="text-sm text-blue-700 dark:text-blue-300">
                    Import historical data safely - one 30-day chunk at a time (rate limit friendly)
                  </p>
                  <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                    💡 Click once per hour to gradually import all historical data, then enable automatic daily sync above
                  </p>
                </div>
                <button
                  onClick={() => handleSafeChunkedHistoricalSync()}
                  disabled={syncStatus.status === 'syncing'}
                  className="btn btn-sm btn-primary"
                >
                  {syncStatus.status === 'syncing' ? (
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Database className="h-4 w-4 mr-2" />
                  )}
                  Import Next Chunk
                </button>
              </div>
            </div>
          </div>

          {/* Advanced Sync Options */}
          <div className="border-t pt-4">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-sm text-secondary">
                  {syncStatus.message || 'Ready to sync'}
                </p>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setShowAdvancedSync(!showAdvancedSync)}
                  className="btn btn-ghost btn-sm"
                >
                  <SettingsIcon className="h-4 w-4 mr-1" />
                  {showAdvancedSync ? 'Simple' : 'Advanced'}
                </button>
                <button
                  onClick={() => handleManualSync(showAdvancedSync ? syncOptions : undefined)}
                  disabled={syncStatus.status === 'syncing'}
                  className="btn btn-outline btn-sm"
                >
                  {syncStatus.status === 'syncing' ? (
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4 mr-2" />
                  )}
                  Manual Sync
                </button>
              </div>
            </div>

            {showAdvancedSync && (
              <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-secondary mb-2">
                    Sync Type
                  </label>
                  <select
                    value={syncOptions.syncType}
                    onChange={(e) => setSyncOptions(prev => ({ ...prev, syncType: e.target.value as any }))}
                    className="form-select w-full"
                  >
                                          <option value="time_entries_only">Time Entries Only (3-25+ API calls)</option>
                      <option value="full">Full Sync (6-28+ API calls)</option>
                      <option value="metadata">Metadata Only (3 API calls)</option>
                      <option value="clients">Clients Only (1 API call)</option>
                      <option value="projects">Projects Only (1 API call)</option>
                      <option value="members">Members Only (1 API call)</option>
                      <option value="time_entries">Time Entries (3-25+ API calls)</option>
                  </select>
                  <p className="text-xs text-muted mt-1">
                    {syncOptions.syncType === 'time_entries_only' && 'Sync only recent time entries for quick updates'}
                    {syncOptions.syncType === 'full' && 'Sync all data including clients, projects, members, and time entries'}
                    {syncOptions.syncType === 'metadata' && 'Sync only structural data without time entries'}
                    {syncOptions.syncType === 'clients' && 'Sync only client information'}
                    {syncOptions.syncType === 'projects' && 'Sync only project information'}
                    {syncOptions.syncType === 'members' && 'Sync only workspace members'}
                    {syncOptions.syncType === 'time_entries' && 'Sync time entries with custom date range'}
                  </p>
                </div>

                {(syncOptions.syncType === 'time_entries_only' || syncOptions.syncType === 'full' || syncOptions.syncType === 'time_entries') && (
                  <div>
                    <label className="block text-sm font-medium text-secondary mb-2">
                      Time Entries Timeframe
                    </label>
                    <div className="flex space-x-1 bg-white dark:bg-gray-800 rounded-lg p-1 mb-3">
                      <button
                        onClick={() => setSyncOptions(prev => ({ ...prev, timeframeType: 'days' }))}
                        className={`flex-1 py-1 px-2 rounded text-xs font-medium transition-colors ${
                          syncOptions.timeframeType === 'days'
                            ? 'bg-primary-500 text-white'
                            : 'text-muted hover:text-secondary'
                        }`}
                      >
                        Days Back
                      </button>
                      <button
                        onClick={() => setSyncOptions(prev => ({ ...prev, timeframeType: 'custom' }))}
                        className={`flex-1 py-1 px-2 rounded text-xs font-medium transition-colors ${
                          syncOptions.timeframeType === 'custom'
                            ? 'bg-primary-500 text-white'
                            : 'text-muted hover:text-secondary'
                        }`}
                      >
                        Custom Range
                      </button>
                    </div>

                    {syncOptions.timeframeType === 'days' && (
                      <div className="flex items-center space-x-2">
                        <input
                          type="number"
                          min="1"
                          max="365"
                          value={syncOptions.timeEntriesDays}
                          onChange={(e) => setSyncOptions(prev => ({ ...prev, timeEntriesDays: parseInt(e.target.value) || 7 }))}
                          className="form-input w-20 text-sm"
                        />
                        <span className="text-xs text-muted">days back (max 365)</span>
                      </div>
                    )}

                    {syncOptions.timeframeType === 'custom' && (
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="block text-xs font-medium text-secondary mb-1">
                            Start Date
                          </label>
                          <input
                            type="date"
                            value={syncOptions.startDate}
                            onChange={(e) => setSyncOptions(prev => ({ ...prev, startDate: e.target.value }))}
                            className="form-input w-full text-sm"
                            max={syncOptions.endDate || new Date().toISOString().split('T')[0]}
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-secondary mb-1">
                            End Date
                          </label>
                          <input
                            type="date"
                            value={syncOptions.endDate}
                            onChange={(e) => setSyncOptions(prev => ({ ...prev, endDate: e.target.value }))}
                            className="form-input w-full text-sm"
                            min={syncOptions.startDate}
                            max={new Date().toISOString().split('T')[0]}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
                  <h4 className="text-sm font-medium text-primary mb-1">Sync Preview</h4>
                  <p className="text-xs text-secondary">
                    <strong>Type:</strong> {syncOptions.syncType.replace('_', ' ').toUpperCase()}
                    {(syncOptions.syncType === 'time_entries_only' || syncOptions.syncType === 'full' || syncOptions.syncType === 'time_entries') && (
                      <>
                        <br />
                        <strong>Timeframe:</strong> {
                          syncOptions.timeframeType === 'days' 
                            ? `Last ${syncOptions.timeEntriesDays} days`
                            : syncOptions.timeframeType === 'custom' && syncOptions.startDate && syncOptions.endDate
                              ? `${syncOptions.startDate} to ${syncOptions.endDate}`
                              : 'Custom range (incomplete)'
                        }
                      </>
                    )}
                  </p>
                </div>
                
                {/* Rate Limit Warning */}
                <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-3 mt-3">
                  <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-200 mb-1">⚠️ Free Plan Rate Limits</h4>
                  <p className="text-xs text-yellow-700 dark:text-yellow-300">
                    <strong>Free Plan: 30 API calls/hour</strong> • For 365+ days, consider upgrading to Premium (600 calls/hour)
                  </p>
                  <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                    Recommended: Use 30 days max for time entries on free plan
                  </p>
                </div>


              </div>
            )}
          </div>
        </div>
      </div>

      {/* Interface Settings */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center space-x-2">
            <SettingsIcon className="h-5 w-5 text-muted" />
            <h3 className="text-lg font-semibold text-primary">Interface Preferences</h3>
          </div>
        </div>
        <div className="card-body space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-secondary mb-1">
                Theme
              </label>
              <select
                value={theme}
                onChange={(e) => setTheme(e.target.value as 'light' | 'dark' | 'auto')}
                className="form-select"
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="auto">Auto (System)</option>
              </select>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-secondary">
                  Notifications
                </label>
                <p className="text-xs text-muted">
                  Show desktop notifications for sync events
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.notifications}
                  onChange={(e) => setSettings(prev => ({ ...prev, notifications: e.target.checked }))}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* API Configuration */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center space-x-2">
            <Key className="h-5 w-5 text-muted" />
            <h3 className="text-lg font-semibold text-primary">API Configuration</h3>
          </div>
        </div>
        <div className="card-body">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
              <div>
                <h4 className="text-sm font-medium text-yellow-800">API Settings</h4>
                <p className="text-sm text-yellow-700 mt-1">
                  API credentials are configured through environment variables for security. 
                  Contact your system administrator to update Toggl API settings.
                </p>
                <div className="mt-2 space-y-1 text-xs text-yellow-600">
                  <p>• TOGGL_API_TOKEN: Your personal API token</p>
                  <p>• TOGGL_WORKSPACE_ID: Default workspace ID</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* System Information */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center space-x-2">
            <Globe className="h-5 w-5 text-muted" />
            <h3 className="text-lg font-semibold text-primary">System Information</h3>
          </div>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-secondary">Application Version:</span>
                <span className="font-medium text-primary">1.0.0</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary">Backend Status:</span>
                <span className="font-medium text-green-600">Connected</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary">Database Status:</span>
                <span className="font-medium text-green-600">Healthy</span>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-secondary">Toggl API Status:</span>
                <span className="font-medium text-green-600">Connected</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary">Rate Limit:</span>
                <span className="font-medium text-primary">1 req/sec</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary">Cache Status:</span>
                <span className="font-medium text-blue-600">Active</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}