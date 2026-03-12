import React from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import { useTheme } from '@mui/material/styles'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatCurrency } from '@/utils/format'
import type { TrendPoint } from '@/types/analytics'

const MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

interface MonthlyTrendProps {
  data: TrendPoint[]
  height?: number
  showBudgetLine?: boolean
  budget?: number | null
  showAverageLine?: boolean
}

export function MonthlyTrend({ data, height = 260, showBudgetLine, budget, showAverageLine = true }: MonthlyTrendProps) {
  const theme = useTheme()

  if (!data.length) {
    return (
      <Box sx={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography color="text.secondary">No data</Typography>
      </Box>
    )
  }

  const chartData = data.map((d) => ({
    ...d,
    total_amount: Math.abs(d.total_amount),
    period: `${MONTH_ABBR[(d.month - 1) % 12]} ${String(d.year).slice(2)}`,
  }))

  // Exclude current (partial) month from average calculation
  const completedMonths = chartData.length > 1 ? chartData.slice(0, -1) : chartData
  const average = completedMonths.reduce((sum, d) => sum + d.total_amount, 0) / completedMonths.length

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
        <XAxis
          dataKey="period"
          tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `₪${(v / 1000).toFixed(0)}k`}
        />
        <Tooltip
          formatter={(value: number) => [formatCurrency(value), 'Spent']}
          contentStyle={{
            background: theme.palette.background.paper,
            border: `1px solid ${theme.palette.divider}`,
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Bar dataKey="total_amount" radius={[4, 4, 0, 0]}>
          {chartData.map((_, i) => (
            <Cell
              key={i}
              fill={theme.palette.primary.main}
              fillOpacity={i === chartData.length - 1 ? 0.55 : 1}
            />
          ))}
        </Bar>
        {showAverageLine && average > 0 && (
          <ReferenceLine
            y={average}
            stroke={theme.palette.info.main}
            strokeWidth={2}
            strokeDasharray="6 3"
            label={{
              value: `Avg ₪${Math.round(average / 1000)}k`,
              fill: theme.palette.info.main,
              fontSize: 12,
              fontWeight: 600,
              position: 'insideTopRight',
            }}
          />
        )}
        {showBudgetLine && budget && (
          <ReferenceLine
            y={budget}
            stroke={theme.palette.warning.dark}
            strokeWidth={2.5}
            strokeDasharray="8 4"
            label={{
              value: `Budget ₪${Math.round(budget / 1000)}k`,
              fill: theme.palette.warning.dark,
              fontSize: 12,
              fontWeight: 600,
              position: 'insideTopRight',
            }}
          />
        )}
      </BarChart>
    </ResponsiveContainer>
  )
}
