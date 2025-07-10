/**
 * Utility functions for formatting data in the UI
 */

/**
 * Format currency values
 */
export function formatCurrency(
  amount: number, 
  currency: 'USD' | 'EUR' = 'USD',
  options: { 
    minimumFractionDigits?: number
    maximumFractionDigits?: number
    compact?: boolean
  } = {}
): string {
  const { minimumFractionDigits = 2, maximumFractionDigits = 2, compact = false } = options
  
  if (compact && amount >= 1000000) {
    return `${currency === 'USD' ? '$' : '€'}${(amount / 1000000).toFixed(1)}M`
  }
  
  if (compact && amount >= 1000) {
    return `${currency === 'USD' ? '$' : '€'}${(amount / 1000).toFixed(1)}K`
  }
  
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits,
    maximumFractionDigits,
  }).format(amount)
}

/**
 * Format hours with proper labels
 */
export function formatHours(
  hours: number,
  options: {
    showMinutes?: boolean
    compact?: boolean
    precision?: number
  } = {}
): string {
  const { showMinutes = false, compact = false, precision = 1 } = options
  
  if (hours === 0) {
    return compact ? '0h' : '0 hours'
  }
  
  if (compact) {
    if (hours >= 1000) {
      return `${(hours / 1000).toFixed(1)}Kh`
    }
    return `${hours.toFixed(precision)}h`
  }
  
  if (showMinutes && hours < 1) {
    const minutes = Math.round(hours * 60)
    return `${minutes}m`
  }
  
  if (showMinutes) {
    const wholeHours = Math.floor(hours)
    const minutes = Math.round((hours - wholeHours) * 60)
    
    if (minutes === 0) {
      return `${wholeHours}h`
    }
    
    return `${wholeHours}h ${minutes}m`
  }
  
  return `${hours.toFixed(precision)}h`
}

/**
 * Format percentages
 */
export function formatPercentage(
  value: number,
  options: {
    precision?: number
    showSign?: boolean
  } = {}
): string {
  const { precision = 1, showSign = false } = options
  
  const formatted = value.toFixed(precision)
  const sign = showSign && value > 0 ? '+' : ''
  
  return `${sign}${formatted}%`
}

/**
 * Format numbers with proper locale formatting
 */
export function formatNumber(
  value: number,
  options: {
    precision?: number
    compact?: boolean
  } = {}
): string {
  const { precision = 0, compact = false } = options
  
  if (compact) {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`
    }
    if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`
    }
  }
  
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  }).format(value)
}

/**
 * Format dates in a readable format
 */
export function formatDate(
  date: string | Date,
  options: {
    includeTime?: boolean
    relative?: boolean
    format?: 'short' | 'medium' | 'long'
  } = {}
): string {
  const { includeTime = false, relative = false, format = 'medium' } = options
  
  const dateObj = typeof date === 'string' ? new Date(date) : date
  
  if (relative) {
    const now = new Date()
    const diff = now.getTime() - dateObj.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    
    if (days === 0) return 'Today'
    if (days === 1) return 'Yesterday'
    if (days < 7) return `${days} days ago`
    if (days < 30) return `${Math.floor(days / 7)} weeks ago`
    if (days < 365) return `${Math.floor(days / 30)} months ago`
    return `${Math.floor(days / 365)} years ago`
  }
  
  const formatOptions: Intl.DateTimeFormatOptions = {}
  
  if (format === 'short') {
    formatOptions.month = '2-digit'
    formatOptions.day = '2-digit'
    formatOptions.year = '2-digit'
  } else if (format === 'medium') {
    formatOptions.month = 'short'
    formatOptions.day = 'numeric'
    formatOptions.year = 'numeric'
  } else {
    formatOptions.month = 'long'
    formatOptions.day = 'numeric'
    formatOptions.year = 'numeric'
  }
  
  if (includeTime) {
    formatOptions.hour = 'numeric'
    formatOptions.minute = '2-digit'
    formatOptions.hour12 = true
  }
  
  return new Intl.DateTimeFormat('en-US', formatOptions).format(dateObj)
}

/**
 * Format date ranges
 */
export function formatDateRange(
  startDate: string | Date,
  endDate: string | Date,
  options: {
    format?: 'short' | 'medium' | 'long'
  } = {}
): string {
  const { format = 'medium' } = options
  
  const start = typeof startDate === 'string' ? new Date(startDate) : startDate
  const end = typeof endDate === 'string' ? new Date(endDate) : endDate
  
  // Same day
  if (start.toDateString() === end.toDateString()) {
    return formatDate(start, { format })
  }
  
  // Same month and year
  if (start.getMonth() === end.getMonth() && start.getFullYear() === end.getFullYear()) {
    if (format === 'short') {
      return `${start.getMonth() + 1}/${start.getDate()}-${end.getDate()}/${start.getFullYear()}`
    }
    return `${start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${end.getDate()}, ${start.getFullYear()}`
  }
  
  // Same year
  if (start.getFullYear() === end.getFullYear()) {
    return `${formatDate(start, { format }).replace(`, ${start.getFullYear()}`, '')} - ${formatDate(end, { format })}`
  }
  
  // Different years
  return `${formatDate(start, { format })} - ${formatDate(end, { format })}`
}

/**
 * Format duration in a human-readable way
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`
  }
  
  if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`
  }
  
  const hours = Math.floor(seconds / 3600)
  const remainingMinutes = Math.floor((seconds % 3600) / 60)
  
  if (remainingMinutes === 0) {
    return `${hours}h`
  }
  
  return `${hours}h ${remainingMinutes}m`
}

/**
 * Format file sizes
 */
export function formatFileSize(bytes: number): string {
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  
  if (bytes === 0) return '0 B'
  
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const size = bytes / Math.pow(1024, i)
  
  return `${size.toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`
}

/**
 * Truncate text with ellipsis
 */
export function truncateText(
  text: string,
  maxLength: number,
  options: {
    suffix?: string
    wordBoundary?: boolean
  } = {}
): string {
  const { suffix = '...', wordBoundary = false } = options
  
  if (text.length <= maxLength) {
    return text
  }
  
  if (wordBoundary) {
    const truncated = text.substring(0, maxLength)
    const lastSpace = truncated.lastIndexOf(' ')
    return lastSpace > 0 
      ? truncated.substring(0, lastSpace) + suffix
      : truncated + suffix
  }
  
  return text.substring(0, maxLength) + suffix
}

/**
 * Format billable percentage with color indication
 */
export function getBillablePercentageColor(percentage: number): string {
  if (percentage >= 90) return 'text-success-600'
  if (percentage >= 80) return 'text-success-500'
  if (percentage >= 70) return 'text-warning-500'
  if (percentage >= 60) return 'text-warning-600'
  return 'text-danger-500'
}

/**
 * Format time entry tags
 */
export function formatTags(tags: string[]): string {
  if (!tags || tags.length === 0) return 'No tags'
  if (tags.length === 1) return tags[0]
  if (tags.length <= 3) return tags.join(', ')
  return `${tags.slice(0, 2).join(', ')} +${tags.length - 2} more`
}