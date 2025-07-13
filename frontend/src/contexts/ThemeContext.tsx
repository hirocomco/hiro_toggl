import { createContext, useContext, useEffect, useState, ReactNode } from 'react'

type Theme = 'light' | 'dark' | 'auto'

interface ThemeContextType {
  theme: Theme
  actualTheme: 'light' | 'dark'
  setTheme: (theme: Theme) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function useTheme() {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

interface ThemeProviderProps {
  children: ReactNode
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window !== 'undefined') {
      const savedTheme = localStorage.getItem('toggl-theme') as Theme
      return savedTheme || 'light'
    }
    return 'light'
  })

  const [actualTheme, setActualTheme] = useState<'light' | 'dark'>('light')

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    
    const updateActualTheme = () => {
      if (theme === 'auto') {
        setActualTheme(mediaQuery.matches ? 'dark' : 'light')
      } else {
        setActualTheme(theme)
      }
    }

    updateActualTheme()
    
    const handleChange = () => {
      if (theme === 'auto') {
        updateActualTheme()
      }
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [theme])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', actualTheme === 'dark')
  }, [actualTheme])

  const handleSetTheme = (newTheme: Theme) => {
    setTheme(newTheme)
    if (typeof window !== 'undefined') {
      localStorage.setItem('toggl-theme', newTheme)
    }
  }

  return (
    <ThemeContext.Provider value={{ theme, actualTheme, setTheme: handleSetTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}