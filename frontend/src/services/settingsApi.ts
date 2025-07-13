/**
 * Settings API service for frontend
 */

import { apiService } from './api'

export interface SettingValue {
  key: string
  value: string | number | boolean | object
  data_type: 'string' | 'integer' | 'float' | 'boolean' | 'json'
  resolved_from: 'system' | 'workspace' | 'client'
  effective_date: string
}

export interface Setting {
  id: number
  key: string
  value: string
  typed_value: string | number | boolean | object
  data_type: 'string' | 'integer' | 'float' | 'boolean' | 'json'
  category: 'general' | 'workspace' | 'sync' | 'ui' | 'api' | 'notification' | 'currency' | 'rate'
  scope: 'system' | 'workspace' | 'client'
  workspace_id?: number
  client_id?: number
  description?: string
  is_readonly: boolean
  effective_date: string
  created_at: string
  updated_at: string
}

export interface CategorySettings {
  category: string
  workspace_id?: number
  client_id?: number
  settings: Record<string, any>
  metadata?: Record<string, Setting>
}

export interface CreateSettingRequest {
  key: string
  value: string | number | boolean | object
  data_type?: 'string' | 'integer' | 'float' | 'boolean' | 'json'
  category?: 'general' | 'workspace' | 'sync' | 'ui' | 'api' | 'notification' | 'currency' | 'rate'
  workspace_id?: number
  client_id?: number
  description?: string
  is_readonly?: boolean
  effective_date?: string
}

export interface UpdateSettingRequest {
  value?: string | number | boolean | object
  data_type?: 'string' | 'integer' | 'float' | 'boolean' | 'json'
  category?: 'general' | 'workspace' | 'sync' | 'ui' | 'api' | 'notification' | 'currency' | 'rate'
  description?: string
  effective_date?: string
}

export interface BulkCreateRequest {
  settings: CreateSettingRequest[]
  workspace_id?: number
  client_id?: number
  effective_date?: string
}

export class SettingsApiService {
  private baseUrl: string

  constructor(baseUrl: string = 'settings') {
    // Fixed: Remove leading slash to prevent /api/api/settings duplication
    this.baseUrl = baseUrl
  }

  /**
   * Get a setting value with hierarchical resolution
   */
  async getSettingValue(
    key: string, 
    workspace_id?: number, 
    client_id?: number, 
    category?: string
  ): Promise<SettingValue> {
    const params = new URLSearchParams()
    params.append('key', key)
    if (workspace_id) params.append('workspace_id', workspace_id.toString())
    if (client_id) params.append('client_id', client_id.toString())
    if (category) params.append('category', category)

    const response = await apiService.get(`${this.baseUrl}/value?${params}`)
    return response.data
  }

  /**
   * Get all settings in a category
   */
  async getCategorySettings(
    category: string,
    workspace_id?: number,
    client_id?: number,
    include_metadata: boolean = false
  ): Promise<CategorySettings> {
    const params = new URLSearchParams()
    params.append('category', category)
    if (workspace_id) params.append('workspace_id', workspace_id.toString())
    if (client_id) params.append('client_id', client_id.toString())
    if (include_metadata) params.append('include_metadata', 'true')

    const response = await apiService.get(`${this.baseUrl}/category/${category}?${params}`)
    return response.data
  }

  /**
   * Get all workspace settings
   */
  async getWorkspaceSettings(
    workspace_id: number,
    category?: string,
    include_system: boolean = true
  ): Promise<{
    workspace_id: number
    settings: Record<string, Record<string, any>>
  }> {
    const params = new URLSearchParams()
    if (category) params.append('category', category)
    if (include_system) params.append('include_system', 'true')

    const response = await apiService.get(`${this.baseUrl}/workspace/${workspace_id}?${params}`)
    return response.data
  }

  /**
   * Create or update a setting
   */
  async createSetting(request: CreateSettingRequest): Promise<Setting> {
    const response = await apiService.post(this.baseUrl, request)
    return response.data
  }

  /**
   * Update an existing setting
   */
  async updateSetting(setting_id: number, request: UpdateSettingRequest): Promise<Setting> {
    const response = await apiService.put(`${this.baseUrl}/${setting_id}`, request)
    return response.data
  }

  /**
   * Delete a setting
   */
  async deleteSetting(setting_id: number): Promise<void> {
    await apiService.delete(`${this.baseUrl}/${setting_id}`)
  }

  /**
   * Create multiple settings in bulk
   */
  async bulkCreateSettings(request: BulkCreateRequest): Promise<{
    created_count: number
    updated_count: number
    settings: Setting[]
  }> {
    const response = await apiService.post(`${this.baseUrl}/bulk`, request)
    return response.data
  }

  /**
   * Initialize default settings for a workspace
   */
  async initializeWorkspaceDefaults(workspace_id: number): Promise<{
    workspace_id: number
    initialized_settings: number
    settings: string[]
  }> {
    const response = await apiService.post(`${this.baseUrl}/initialize/workspace/${workspace_id}`)
    return response.data
  }

  /**
   * Get setting history
   */
  async getSettingHistory(
    key: string,
    workspace_id?: number,
    client_id?: number
  ): Promise<{
    key: string
    workspace_id?: number
    client_id?: number
    history: Setting[]
  }> {
    const params = new URLSearchParams()
    params.append('key', key)
    if (workspace_id) params.append('workspace_id', workspace_id.toString())
    if (client_id) params.append('client_id', client_id.toString())

    const response = await apiService.get(`${this.baseUrl}/history/${key}?${params}`)
    return response.data
  }

  /**
   * Validate a setting value
   */
  async validateSetting(
    key: string,
    value: any,
    data_type: 'string' | 'integer' | 'float' | 'boolean' | 'json'
  ): Promise<{
    is_valid: boolean
    converted_value?: any
    error_message?: string
  }> {
    const response = await apiService.post(`${this.baseUrl}/validate`, {
      key,
      value,
      data_type
    })
    return response.data
  }

  /**
   * Get system overview
   */
  async getSystemOverview(): Promise<{
    total_settings: number
    by_category: Record<string, number>
    by_scope: Record<string, number>
    readonly_count: number
    recent_changes: Setting[]
  }> {
    const response = await apiService.get(`${this.baseUrl}/system/overview`)
    return response.data
  }
}

// Create singleton instance
export const settingsApi = new SettingsApiService()

// Helper functions for common settings operations
export const settingsHelpers = {
  /**
   * Get multiple settings by keys
   */
  async getMultipleSettings(
    keys: string[],
    workspace_id?: number,
    client_id?: number
  ): Promise<Record<string, any>> {
    const settings: Record<string, any> = {}
    
    try {
      const promises = keys.map(async (key) => {
        try {
          const setting = await settingsApi.getSettingValue(key, workspace_id, client_id)
          // Handle boolean conversion - backend might return 1/0 instead of true/false
          let value = setting.value
          if (setting.data_type === 'boolean') {
            value = value === true || value === 1 || value === '1' || value === 'true'
          }
          return { key, value }
        } catch (error) {
          console.warn(`Failed to get setting '${key}':`, error)
          return { key, value: null }
        }
      })
      
      const results = await Promise.all(promises)
      results.forEach(({ key, value }) => {
        settings[key] = value
      })
    } catch (error) {
      console.error('Failed to get multiple settings:', error)
    }
    
    return settings
  },

  /**
   * Set multiple settings at once
   */
  async setMultipleSettings(
    settingsData: Record<string, any>,
    workspace_id?: number,
    client_id?: number,
    category: string = 'general'
  ): Promise<Setting[]> {
    const createRequests: CreateSettingRequest[] = Object.entries(settingsData).map(([key, value]) => ({
      key,
      value,
      data_type: typeof value === 'number' ? 'integer' : typeof value === 'boolean' ? 'boolean' : 'string',
      category: category as any,
      workspace_id,
      client_id
    }))

    const result = await settingsApi.bulkCreateSettings({
      settings: createRequests,
      workspace_id,
      client_id
    })

    return result.settings
  },

  /**
   * Get application configuration settings
   */
  async getAppConfig(workspace_id?: number): Promise<{
    workspace_id?: string
    default_currency: string
    auto_sync: boolean
    sync_interval: number
    notifications: boolean
  }> {
    const defaultConfig = {
      workspace_id: '842441', // Default workspace ID
      default_currency: 'USD',
      auto_sync: true,
      sync_interval: 30,
      notifications: true
    }

    try {
      // Get individual settings from system level (no workspace_id)
      const configKeys = ['workspace_id', 'default_currency', 'auto_sync', 'sync_interval', 'notifications']
      const settings = await settingsHelpers.getMultipleSettings(configKeys)
      
      return {
        workspace_id: settings.workspace_id || defaultConfig.workspace_id,
        default_currency: settings.default_currency || defaultConfig.default_currency,
        auto_sync: settings.auto_sync ?? defaultConfig.auto_sync,
        sync_interval: settings.sync_interval || defaultConfig.sync_interval,
        notifications: settings.notifications ?? defaultConfig.notifications
      }
    } catch (error) {
      console.error('Failed to get app config:', error)
      return defaultConfig
    }
  },

  /**
   * Save application configuration settings
   */
  async saveAppConfig(
    config: {
      workspace_id?: string
      default_currency?: string
      auto_sync?: boolean
      sync_interval?: number
      notifications?: boolean
    },
    workspace_id?: number
  ): Promise<void> {
    const settingsToSave: CreateSettingRequest[] = []
    
    if (config.workspace_id !== undefined) {
      settingsToSave.push({
        key: 'workspace_id',
        value: config.workspace_id,
        data_type: 'string',
        category: 'api'
      })
    }
    
    if (config.default_currency !== undefined) {
      settingsToSave.push({
        key: 'default_currency',
        value: config.default_currency,
        data_type: 'string',
        category: 'currency'
      })
    }
    
    if (config.auto_sync !== undefined) {
      settingsToSave.push({
        key: 'auto_sync',
        value: config.auto_sync,
        data_type: 'boolean',
        category: 'sync'
      })
    }
    
    if (config.sync_interval !== undefined) {
      settingsToSave.push({
        key: 'sync_interval',
        value: config.sync_interval,
        data_type: 'integer',
        category: 'sync'
      })
    }
    
    if (config.notifications !== undefined) {
      settingsToSave.push({
        key: 'notifications',
        value: config.notifications,
        data_type: 'boolean',
        category: 'notification'
      })
    }

    if (settingsToSave.length > 0) {
      await settingsApi.bulkCreateSettings({
        settings: settingsToSave,
        workspace_id
      })
    }
  }
}