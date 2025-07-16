import { useState } from 'react'
import { Calendar, ChevronDown } from 'lucide-react'

export interface DateRange {
  start_date?: string
  end_date?: string
}

export interface DateRangePickerProps {
  value: string
  onChange: (period: string, customRange?: DateRange) => void
  className?: string
}

const PRESET_OPTIONS = [
  { value: 'last_7_days', label: 'Last 7 days' },
  { value: 'last_30_days', label: 'Last 30 days' },
  { value: 'last_90_days', label: 'Last 90 days' },
  { value: 'this_month', label: 'This month' },
  { value: 'last_month', label: 'Last month' },
  { value: 'this_quarter', label: 'This quarter' },
  { value: 'last_quarter', label: 'Last quarter' },
  { value: 'this_year', label: 'This year' },
  { value: 'custom', label: 'Custom range' }
]

export default function DateRangePicker({ value, onChange, className = '' }: DateRangePickerProps) {
  const [showCustom, setShowCustom] = useState(value === 'custom')
  const [customRange, setCustomRange] = useState<DateRange>({})

  const handlePeriodChange = (newPeriod: string) => {
    if (newPeriod === 'custom') {
      setShowCustom(true)
      return
    }
    
    setShowCustom(false)
    onChange(newPeriod)
  }

  const handleCustomRangeChange = (field: 'start_date' | 'end_date', value: string) => {
    const newRange = { ...customRange, [field]: value }
    setCustomRange(newRange)
    
    if (newRange.start_date && newRange.end_date) {
      onChange('custom', newRange)
    }
  }

  const selectedLabel = PRESET_OPTIONS.find(opt => opt.value === value)?.label || 'Select period'

  return (
    <div className={`relative ${className}`}>
      <div className="flex items-center space-x-2">
        <Calendar className="h-4 w-4 text-muted" />
        <div className="relative">
          <select
            value={showCustom ? 'custom' : value}
            onChange={(e) => handlePeriodChange(e.target.value)}
            className="form-select w-48 pr-8 appearance-none bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            {PRESET_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted pointer-events-none" />
        </div>
      </div>

      {showCustom && (
        <div className="absolute top-full left-0 mt-2 p-4 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg z-10 min-w-80">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-secondary mb-1">
                Start Date
              </label>
              <input
                type="date"
                value={customRange.start_date || ''}
                onChange={(e) => handleCustomRangeChange('start_date', e.target.value)}
                className="form-input w-full"
                max={customRange.end_date || undefined}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary mb-1">
                End Date
              </label>
              <input
                type="date"
                value={customRange.end_date || ''}
                onChange={(e) => handleCustomRangeChange('end_date', e.target.value)}
                className="form-input w-full"
                min={customRange.start_date || undefined}
                max={new Date().toISOString().split('T')[0]}
              />
            </div>
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => {
                  setShowCustom(false)
                  setCustomRange({})
                  onChange('last_30_days')
                }}
                className="btn btn-ghost btn-sm"
              >
                Cancel
              </button>
              <button
                onClick={() => setShowCustom(false)}
                disabled={!customRange.start_date || !customRange.end_date}
                className="btn btn-primary btn-sm"
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}