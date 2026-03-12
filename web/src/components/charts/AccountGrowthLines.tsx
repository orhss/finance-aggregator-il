import React, { useMemo } from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import { useTheme } from '@mui/material/styles'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatCurrency } from '@/utils/format'
import type { PortfolioProgression } from '@/types/balance'

const COLORS = ['#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#14b8a6']

interface Props {
  data: PortfolioProgression
  height?: number
}

export function AccountGrowthLines({ data, height = 280 }: Props) {
  const theme = useTheme()

  const chartData = useMemo(() => {
    if (!data.points.length) return []

    // Group points by date
    const byDate = new Map<string, Map<string, number>>()
    for (const p of data.points) {
      if (!byDate.has(p.date)) byDate.set(p.date, new Map())
      byDate.get(p.date)!.set(p.series, p.total_amount)
    }

    // Forward-fill
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
        <Typography color="text.secondary">No account data</Typography>
      </Box>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
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
          <Line
            key={s}
            type="monotone"
            dataKey={s}
            stroke={COLORS[i % COLORS.length]}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
