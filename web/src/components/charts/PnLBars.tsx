import React from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import { useTheme } from '@mui/material/styles'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatCurrency, formatPercentage } from '@/utils/format'
import type { PnLSummaryItem } from '@/types/balance'

interface Props {
  data: PnLSummaryItem[]
  height?: number
}

export function PnLBars({ data, height = 280 }: Props) {
  const theme = useTheme()

  if (!data.length) {
    return (
      <Box sx={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography color="text.secondary">No P&L data</Typography>
      </Box>
    )
  }

  const chartData = data.map((d) => ({
    name: d.label,
    pnl: d.profit_loss ?? 0,
    percentage: d.profit_loss_percentage,
  }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 8, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `₪${(v / 1000).toFixed(0)}k`}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
          tickLine={false}
          axisLine={false}
          width={120}
        />
        <Tooltip
          formatter={(value: number, _name: string, props: { payload?: { percentage?: number | null } }) => {
            const pct = props.payload?.percentage
            const label = pct != null ? `${formatCurrency(value)} (${formatPercentage(pct)})` : formatCurrency(value)
            return [label, 'P&L']
          }}
          contentStyle={{
            background: theme.palette.background.paper,
            border: `1px solid ${theme.palette.divider}`,
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Bar dataKey="pnl" radius={[0, 4, 4, 0]}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={entry.pnl >= 0 ? '#10b981' : '#ef4444'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
