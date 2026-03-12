import React from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import { useTheme } from '@mui/material/styles'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { formatCurrency } from '@/utils/format'
import type { CategoryBreakdownItem } from '@/types/analytics'

const COLORS = [
  '#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b',
  '#ef4444', '#ec4899', '#f97316', '#84cc16', '#64748b',
]

interface SpendingDonutProps {
  data: CategoryBreakdownItem[]
  height?: number
}

export function SpendingDonut({ data, height = 260 }: SpendingDonutProps) {
  const theme = useTheme()
  const top = data.slice(0, 10)

  if (!top.length) {
    return (
      <Box sx={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography color="text.secondary">No data</Typography>
      </Box>
    )
  }

  const top10 = top.map((d) => ({ ...d, total_amount: Math.abs(d.total_amount) })).filter((d) => d.total_amount > 0)

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={top10}
          cx="38%"
          cy="50%"
          innerRadius={55}
          outerRadius={90}
          dataKey="total_amount"
          nameKey="category"
          paddingAngle={2}
          label={({ percent }) => (percent > 0.06 ? `${(percent * 100).toFixed(0)}%` : '')}
          labelLine={false}
        >
          {top10.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number, name: string) => [formatCurrency(value), name]}
          contentStyle={{
            background: theme.palette.background.paper,
            border: `1px solid ${theme.palette.divider}`,
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Legend
          layout="vertical"
          align="right"
          verticalAlign="middle"
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: 11, paddingLeft: 8, lineHeight: '20px' }}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
