import { createContext, useContext, useState, useEffect } from 'react'
import { DateRange } from '@/components/ui/DateRangePicker'

interface DateContextType {
  selectedPeriod: string
  customRange: DateRange | undefined
  setDateRange: (period: string, range?: DateRange) => void
}

const DateContext = createContext<DateContextType | undefined>(undefined)

export const useDateContext = () => {
  const context = useContext(DateContext)
  if (!context) {
    throw new Error('useDateContext must be used within a DateProvider')
  }
  return context
}

const DATE_STORAGE_KEY = 'toggle_date_filter'

export const DateProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [selectedPeriod, setSelectedPeriod] = useState('last_30_days')
  const [customRange, setCustomRange] = useState<DateRange | undefined>()

  // Load saved date preferences on mount
  useEffect(() => {
    const saved = localStorage.getItem(DATE_STORAGE_KEY)
    if (saved) {
      try {
        const { period, range } = JSON.parse(saved)
        setSelectedPeriod(period)
        setCustomRange(range)
      } catch (err) {
        console.warn('Failed to parse saved date preferences:', err)
      }
    }
  }, [])

  // Save date preferences to localStorage
  useEffect(() => {
    const datePrefs = {
      period: selectedPeriod,
      range: customRange
    }
    localStorage.setItem(DATE_STORAGE_KEY, JSON.stringify(datePrefs))
  }, [selectedPeriod, customRange])

  const setDateRange = (period: string, range?: DateRange) => {
    setSelectedPeriod(period)
    setCustomRange(range)
  }

  const value: DateContextType = {
    selectedPeriod,
    customRange,
    setDateRange
  }

  return (
    <DateContext.Provider value={value}>
      {children}
    </DateContext.Provider>
  )
}