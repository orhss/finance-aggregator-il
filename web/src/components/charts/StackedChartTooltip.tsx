import React from 'react'
import { useTheme } from '@mui/material/styles'
import type { NameType, ValueType } from 'recharts/types/component/DefaultTooltipContent'
import type { TooltipProps } from 'recharts'
import { formatCurrency } from '@/utils/format'

interface Props extends TooltipProps<ValueType, NameType> {
  hidden: Set<string>
}

export function StackedChartTooltip({ active, payload, label, hidden }: Props) {
  const theme = useTheme()

  if (!active || !payload?.length) return null

  const visible = payload.filter((p) => !hidden.has(String(p.dataKey)) && (Number(p.value) || 0) > 0)
  const total = visible.reduce((sum, p) => sum + (Number(p.value) || 0), 0)

  return (
    <div
      style={{
        background: theme.palette.background.paper,
        border: `1px solid ${theme.palette.divider}`,
        borderRadius: 8,
        fontSize: 12,
        padding: '8px 12px',
      }}
    >
      <div style={{ marginBottom: 4, fontWeight: 600 }}>{label}</div>
      {visible
        .sort((a, b) => (Number(b.value) || 0) - (Number(a.value) || 0))
        .map((entry) => (
          <div
            key={entry.dataKey}
            style={{ display: 'flex', justifyContent: 'space-between', gap: 16, color: entry.color }}
          >
            <span>{entry.name}</span>
            <span>{formatCurrency(Number(entry.value) || 0)}</span>
          </div>
        ))}
      <div
        style={{
          borderTop: `1px solid ${theme.palette.divider}`,
          marginTop: 4,
          paddingTop: 4,
          fontWeight: 600,
          display: 'flex',
          justifyContent: 'space-between',
          gap: 16,
        }}
      >
        <span>Total</span>
        <span>{formatCurrency(total)}</span>
      </div>
    </div>
  )
}
