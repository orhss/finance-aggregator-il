import React, { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { ThemeProvider } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import { createAppTheme } from '@/theme'

type Mode = 'light' | 'dark'

interface ThemeContextValue {
  mode: Mode
  toggleMode: () => void
}

const ThemeContext = createContext<ThemeContextValue>({ mode: 'light', toggleMode: () => {} })

export function AppThemeProvider({ children }: { children: React.ReactNode }) {
  const stored = (localStorage.getItem('theme_mode') as Mode) || 'light'
  const [mode, setMode] = useState<Mode>(stored)

  const toggleMode = useCallback(() => {
    setMode((prev) => {
      const next = prev === 'light' ? 'dark' : 'light'
      localStorage.setItem('theme_mode', next)
      return next
    })
  }, [])

  const theme = useMemo(() => createAppTheme(mode), [mode])

  return (
    <ThemeContext.Provider value={{ mode, toggleMode }}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ThemeContext.Provider>
  )
}

export const useThemeMode = () => useContext(ThemeContext)
