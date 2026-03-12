import { createTheme } from '@mui/material/styles'
import { light, dark } from './palette'

export function createAppTheme(mode: 'light' | 'dark') {
  const p = mode === 'light' ? light : dark

  return createTheme({
    palette: {
      mode,
      primary: { main: p.primary },
      secondary: { main: p.secondary },
      success: { main: p.success },
      warning: { main: p.warning },
      error: { main: p.error },
      info: { main: p.info },
      background: {
        default: p.bgPrimary,
        paper: p.bgSecondary,
      },
      text: {
        primary: p.textPrimary,
        secondary: p.textSecondary,
      },
      divider: p.borderMedium,
    },
    typography: {
      fontFamily: '"Inter", "Roboto", "Helvetica Neue", Arial, sans-serif',
      h1: { fontSize: '2rem', fontWeight: 700 },
      h2: { fontSize: '1.5rem', fontWeight: 600 },
      h3: { fontSize: '1.25rem', fontWeight: 600 },
      h4: { fontSize: '1.125rem', fontWeight: 600 },
      h5: { fontSize: '1rem', fontWeight: 600 },
      h6: { fontSize: '0.875rem', fontWeight: 600 },
    },
    shape: { borderRadius: 12 },
    components: {
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: 16,
            border: `1px solid ${p.borderLight}`,
            boxShadow: mode === 'light'
              ? '0 1px 4px rgba(0,0,0,0.06)'
              : '0 0 16px rgba(255,255,255,0.04)',
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: { textTransform: 'none', borderRadius: 8, fontWeight: 500 },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: { borderRadius: 8 },
        },
      },
      MuiTextField: {
        defaultProps: { size: 'small' },
      },
    },
  })
}

// Financial color tokens (not in MUI palette)
export const financialColors = (mode: 'light' | 'dark') => ({
  income: mode === 'light' ? light.income : dark.income,
  expense: mode === 'light' ? light.expense : dark.expense,
  neutral: mode === 'light' ? light.neutral : dark.neutral,
  chart: mode === 'light' ? light.chart : dark.chart,
})
