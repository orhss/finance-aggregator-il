import React, { useMemo } from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import { useTheme } from '@mui/material/styles'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatCurrency } from '@/utils/format'
import type { PortfolioProgression as PortfolioData } from '@/types/balance'

const STACK_COLORS = ['#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b']

interface Props {
  data: PortfolioData
  height?: number
}

export function PortfolioProgression({ data, height = 300 }: Props) {
  const theme = useTheme()

  const chartData = useMemo(() => {
    if (!data.points.length) return []

    // Group points by date
    const byDate = new Map<string, Map<string, number>>()
    for (const p of data.points) {
      if (!byDate.has(p.date)) byDate.set(p.date, new Map())
      byDate.get(p.date)!.set(p.series, p.total_amount)
    }

    // Forward-fill: carry last known value per series
    const sortedDates = Array.from(byDate.keys()).sort()
    const lastKnown: Record<string, number> = {}
    const rows: Record<string, string | number>[] = []

    for (const d of sortedDates) {
      const dateMap = byDate.get(d)!
      const row: Record<string, string | number> = {
        date: new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      }
      for (const series of data.series_names) {
        const val = dateMap.get(series)
        if (val != null) lastKnown[series] = val
        row[series] = lastKnown[series] ?? 0
      }
      rows.push(row)
    }
    return rows
  }, [data])

  if (!chartData.length) {
    return (
      <Box sx={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography color="text.secondary">No investment data</Typography>
      </Box>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
        <defs>
          {data.series_names.map((s, i) => (
            <linearGradient key={s} id={`portfolioGrad-${i}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={STACK_COLORS[i % STACK_COLORS.length]} stopOpacity={0.4} />
              <stop offset="95%" stopColor={STACK_COLORS[i % STACK_COLORS.length]} stopOpacity={0.05} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
        <XAxis
          dataKey="date"
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
          formatter={(value: number, name: string) => [formatCurrency(value), name]}
          contentStyle={{
            background: theme.palette.background.paper,
            border: `1px solid ${theme.palette.divider}`,
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {data.series_names.map((s, i) => (
          <Area
            key={s}
            type="monotone"
            dataKey={s}
            stackId="1"
            stroke={STACK_COLORS[i % STACK_COLORS.length]}
            fill={`url(#portfolioGrad-${i})`}
            strokeWidth={2}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  )
}
