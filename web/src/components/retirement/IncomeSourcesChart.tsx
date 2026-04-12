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
import { CHART_COLORS } from '@/utils/constants'
import { useChartLegendToggle } from '@/hooks/useChartLegendToggle'
import { StackedChartTooltip } from '@/components/charts/StackedChartTooltip'
import type { MonthlyRow } from '@/types/retirement'

interface Props {
  monthly: MonthlyRow[]
  persons: string[]
  height?: number
}

export function IncomeSourcesChart({ monthly, persons, height = 280 }: Props) {
  const theme = useTheme()
  const { hidden, handleLegendClick } = useChartLegendToggle()

  const { chartData, seriesNames } = useMemo(() => {
    if (!monthly.length) return { chartData: [], seriesNames: [] }

    const names = [
      'Salary',
      'Portfolio Withdrawal',
      'KH Withdrawal',
      ...persons.map((p) => `Pension (${p})`),
      ...persons.map((p) => `Social Security (${p})`),
    ]

    // Sample points
    const step = monthly.length > 600 ? 3 : monthly.length > 300 ? 2 : 1
    const sampled = monthly.filter((_, i) => i % step === 0 || i === monthly.length - 1)

    const data = sampled.map((r) => {
      const row: Record<string, number> = { age: Math.round(r.age * 10) / 10 }
      row['Salary'] = Math.max(0, r.income)
      row['Portfolio Withdrawal'] = Math.max(0, r.withdrawal_portfolio)
      row['KH Withdrawal'] = Math.max(0, r.withdrawal_kh.reduce((s, v) => s + v, 0))
      for (let i = 0; i < persons.length; i++) {
        const muk = r.pension_mukeret[i] || 0
        const maz = r.pension_mazka[i] || 0
        row[`Pension (${persons[i]})`] = Math.max(0, muk + maz)
        row[`Social Security (${persons[i]})`] = Math.max(0, r.old_age[i] || 0)
      }
      return row
    })

    // Filter out series that are always zero
    const activeNames = names.filter((name) => data.some((row) => (row[name] || 0) > 0))

    return { chartData: data, seriesNames: activeNames }
  }, [monthly, persons])

  if (!chartData.length) {
    return (
      <Box sx={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography color="text.secondary">No data</Typography>
      </Box>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
        <defs>
          {seriesNames.map((s, i) => (
            <linearGradient key={s} id={`incomeGrad-${i}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={0.4} />
              <stop offset="95%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={0.05} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
        <XAxis
          dataKey="age"
          tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
          tickLine={false}
          axisLine={false}
          type="number"
          domain={['dataMin', 'dataMax']}
          tickFormatter={(v) => `${Math.round(v)}`}
          interval="preserveStartEnd"
          tickCount={Math.ceil(((chartData[chartData.length - 1]?.age ?? 0) - (chartData[0]?.age ?? 0)) / 5) + 1}
        />
        <YAxis
          tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `₪${(v / 1000).toFixed(0)}k`}
        />
        <Tooltip content={(props) => <StackedChartTooltip {...props} hidden={hidden} />} />
        <Legend
          wrapperStyle={{ fontSize: 11, cursor: 'pointer' }}
          onClick={handleLegendClick}
          formatter={(value: string) => (
            <span style={{ color: hidden.has(value) ? theme.palette.text.disabled : undefined }}>{value}</span>
          )}
        />
        {seriesNames.map((s, i) => (
          <Area
            key={s}
            type="monotone"
            dataKey={s}
            stackId="1"
            stroke={CHART_COLORS[i % CHART_COLORS.length]}
            fill={`url(#incomeGrad-${i})`}
            strokeWidth={2}
            hide={hidden.has(s)}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  )
}
