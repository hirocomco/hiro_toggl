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

export default function Settings() {
  const [settings, setSettings] = useState({
    workspace_id: '123456',
    default_currency: 'USD',
    sync_interval: 30,
    auto_sync: true,
    notifications: true,
    theme: 'light'
  })
  const [syncStatus, setSyncStatus] = useState<{
    last_sync: string | null
    status: 'idle' | 'syncing' | 'success' | 'error'
    message?: string
  }>({
    last_sync: null,
    status: 'idle'
  })
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
      
      // In a real app, this would load from backend
      // For now, we'll just simulate loading
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      const savedSettings = localStorage.getItem('toggl-settings')
      if (savedSettings) {
        setSettings(JSON.parse(savedSettings))
      }
    } catch (err: any) {
      setError('Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  const loadSyncStatus = async () => {
    try {
      // Simulate sync status check
      const lastSync = localStorage.getItem('last-sync')
      setSyncStatus({
        last_sync: lastSync,
        status: lastSync ? 'success' : 'idle',
        message: lastSync ? 'Data synchronized successfully' : 'No sync performed yet'
      })
    } catch (err: any) {
      setSyncStatus({
        last_sync: null,
        status: 'error',
        message: 'Failed to check sync status'
      })
    }
  }

  const handleSaveSettings = async () => {
    try {
      setSaving(true)
      
      // Save to localStorage (in real app, would save to backend)
      localStorage.setItem('toggl-settings', JSON.stringify(settings))
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // Show success message briefly
      setSyncStatus({
        ...syncStatus,
        status: 'success',
        message: 'Settings saved successfully'
      })
      
      setTimeout(() => {
        setSyncStatus(prev => ({ ...prev, status: 'idle' }))
      }, 3000)
    } catch (err: any) {
      setError('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleManualSync = async () => {
    try {
      setSyncStatus({ ...syncStatus, status: 'syncing' })
      
      // Simulate sync process
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      const now = new Date().toISOString()
      localStorage.setItem('last-sync', now)
      
      setSyncStatus({
        last_sync: now,
        status: 'success',
        message: 'Manual sync completed successfully'
      })
      
      setTimeout(() => {
        setSyncStatus(prev => ({ ...prev, status: 'idle' }))
      }, 3000)
    } catch (err: any) {
      setSyncStatus({
        last_sync: syncStatus.last_sync,
        status: 'error',
        message: 'Sync failed. Please try again.'
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
          <h2 className="text-xl font-semibold text-gray-900">Settings</h2>
          <p className="text-sm text-gray-500">
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
            <User className="h-5 w-5 text-gray-500" />
            <h3 className="text-lg font-semibold">Workspace Configuration</h3>
          </div>
        </div>
        <div className="card-body space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Workspace ID
              </label>
              <input
                type="text"
                value={settings.workspace_id}
                onChange={(e) => setSettings(prev => ({ ...prev, workspace_id: e.target.value }))}
                className="form-input"
                placeholder="Your Toggl workspace ID"
              />
              <p className="text-xs text-gray-500 mt-1">
                Find this in your Toggl workspace settings
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
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
            <Database className="h-5 w-5 text-gray-500" />
            <h3 className="text-lg font-semibold">Data Synchronization</h3>
          </div>
        </div>
        <div className="card-body space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Automatic Sync
              </label>
              <p className="text-xs text-gray-500">
                Automatically sync data from Toggl at regular intervals
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
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Sync Interval (minutes)
              </label>
              <select
                value={settings.sync_interval}
                onChange={(e) => setSettings(prev => ({ ...prev, sync_interval: parseInt(e.target.value) }))}
                className="form-select"
                disabled={!settings.auto_sync}
              >
                <option value={15}>15 minutes</option>
                <option value={30}>30 minutes</option>
                <option value={60}>1 hour</option>
                <option value={120}>2 hours</option>
                <option value={360}>6 hours</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
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
                  <span className="text-sm text-gray-600">
                    {syncStatus.last_sync 
                      ? new Date(syncStatus.last_sync).toLocaleString()
                      : 'Never'
                    }
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-4 border-t">
            <div>
              <p className="text-sm text-gray-600">
                {syncStatus.message || 'Ready to sync'}
              </p>
            </div>
            <button
              onClick={handleManualSync}
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
      </div>

      {/* Interface Settings */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center space-x-2">
            <SettingsIcon className="h-5 w-5 text-gray-500" />
            <h3 className="text-lg font-semibold">Interface Preferences</h3>
          </div>
        </div>
        <div className="card-body space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Theme
              </label>
              <select
                value={settings.theme}
                onChange={(e) => setSettings(prev => ({ ...prev, theme: e.target.value }))}
                className="form-select"
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="auto">Auto (System)</option>
              </select>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  Notifications
                </label>
                <p className="text-xs text-gray-500">
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
            <Key className="h-5 w-5 text-gray-500" />
            <h3 className="text-lg font-semibold">API Configuration</h3>
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
            <Globe className="h-5 w-5 text-gray-500" />
            <h3 className="text-lg font-semibold">System Information</h3>
          </div>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-600">Application Version:</span>
                <span className="font-medium">1.0.0</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Backend Status:</span>
                <span className="font-medium text-green-600">Connected</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Database Status:</span>
                <span className="font-medium text-green-600">Healthy</span>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-600">Toggl API Status:</span>
                <span className="font-medium text-green-600">Connected</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Rate Limit:</span>
                <span className="font-medium">1 req/sec</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Cache Status:</span>
                <span className="font-medium text-blue-600">Active</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}