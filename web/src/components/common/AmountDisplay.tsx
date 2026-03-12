import React from 'react'
import Typography from '@mui/material/Typography'
import { useTheme } from '@mui/material/styles'
import { usePrivacy } from '@/contexts/PrivacyContext'
import { formatCurrency } from '@/utils/format'

interface AmountDisplayProps {
  amount: number | null | undefined
  currency?: string
  variant?: 'body1' | 'body2' | 'h4' | 'h5' | 'h6' | 'subtitle1' | 'subtitle2'
  showColor?: boolean
  forceShow?: boolean // ignore privacy mask
  sx?: object
}

export function AmountDisplay({
  amount,
  currency = '₪',
  variant = 'body1',
  showColor = true,
  forceShow = false,
  sx,
}: AmountDisplayProps) {
  const { maskBalances } = usePrivacy()
  const theme = useTheme()

  if (maskBalances && !forceShow) {
    return (
      <Typography variant={variant} sx={{ fontFamily: 'monospace', letterSpacing: 2, ...sx }}>
        ••••••
      </Typography>
    )
  }

  if (amount == null) {
    return (
      <Typography variant={variant} color="text.secondary" sx={sx}>
        N/A
      </Typography>
    )
  }

  const color = showColor
    ? amount < 0
      ? theme.palette.mode === 'light'
        ? '#dc2626'
        : '#f87171'
      : amount > 0
      ? theme.palette.mode === 'light'
        ? '#16a34a'
        : '#34d399'
      : 'text.secondary'
    : 'text.primary'

  return (
    <Typography variant={variant} sx={{ color, fontVariantNumeric: 'tabular-nums', fontWeight: 500, ...sx }}>
      {formatCurrency(amount, currency)}
    </Typography>
  )
}
