import React from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import { useTheme } from '@mui/material/styles'
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatCurrency } from '@/utils/format'
import { getCategoryIcon } from '@/utils/constants'
import type { CategoryBreakdownItem } from '@/types/analytics'

interface CategoryBarsProps {
  data: CategoryBreakdownItem[]
  height?: number
  limit?: number
}

export function CategoryBars({ data, height = 300, limit = 8 }: CategoryBarsProps) {
  const theme = useTheme()
  const top = data.slice(0, limit)

  if (!top.length) {
    return (
      <Box sx={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography color="text.secondary">No data</Typography>
      </Box>
    )
  }

  const chartData = top.map((d) => ({ ...d, label: `${getCategoryIcon(d.category)} ${d.category}` }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 60, left: 8, bottom: 0 }}>
        <XAxis
          type="number"
          tick={{ fontSize: 10, fill: theme.palette.text.secondary }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `₪${(v / 1000).toFixed(0)}k`}
        />
        <YAxis
          type="category"
          dataKey="label"
          width={130}
          tick={{ fontSize: 11, fill: theme.palette.text.primary }}
          tickLine={false}
          axisLine={false}
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
        <Bar dataKey="total_amount" radius={[0, 4, 4, 0]} label={{ position: 'right', fontSize: 10, formatter: (v: number) => formatCurrency(v) }}>
          {chartData.map((_, i) => (
            <Cell key={i} fill={theme.palette.primary.main} fillOpacity={1 - i * 0.07} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
