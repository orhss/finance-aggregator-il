import React, { useMemo } from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import { useTheme } from '@mui/material/styles'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatAxisValue, formatCurrency } from '@/utils/format'
import type { Milestone, MonthlyRow, SimulationSummary } from '@/types/retirement'

interface Props {
  monthly: MonthlyRow[]
  summary: SimulationSummary
  milestones: Milestone[]
  height?: number
}

export function NetWorthChart({ monthly, summary, milestones, height = 360 }: Props) {
  const theme = useTheme()

  const chartData = useMemo(() => {
    // Sample every N months if too many points for smooth rendering
    const step = monthly.length > 600 ? 3 : monthly.length > 300 ? 2 : 1
    const sampled = monthly.filter((_, i) => i % step === 0 || i === monthly.length - 1)
    return sampled.map((r) => ({
      age: Math.round(r.age * 10) / 10,
      nw: r.net_worth,
    }))
  }, [monthly])

  const fireAge = summary.fire_age
  const minNwAge = summary.min_nw_age
  const minNw = summary.min_nw

  // Find pension/old-age milestones for reference lines
  const pensionMilestones = milestones.filter((m) => m.type === 'pension_conversion')
  const oldAgeMilestones = milestones.filter((m) => m.type === 'old_age_start')

  if (!chartData.length) {
    return (
      <Box sx={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography color="text.secondary">No data</Typography>
      </Box>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 20, right: 40, left: -8, bottom: 0 }}>
        <defs>
          <linearGradient id="nwGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={theme.palette.primary.main} stopOpacity={0.3} />
            <stop offset="95%" stopColor={theme.palette.primary.main} stopOpacity={0.02} />
          </linearGradient>
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
          tickFormatter={formatAxisValue}
        />
        <Tooltip
          formatter={(value: number) => [formatCurrency(value), 'Net Worth']}
          labelFormatter={(label) => `Age ${label}`}
          contentStyle={{
            background: theme.palette.background.paper,
            border: `1px solid ${theme.palette.divider}`,
            borderRadius: 8,
            fontSize: 12,
          }}
        />

        {/* FIRE line */}
        <ReferenceLine
          x={fireAge}
          stroke={theme.palette.success.main}
          strokeDasharray="6 3"
          label={{
            value: 'FIRE',
            position: 'top',
            fill: theme.palette.success.main,
            fontSize: 11,
          }}
        />

        {/* Pension conversion lines — position at primary person's age on X axis */}
        {pensionMilestones.map((m, i) => (
          <ReferenceLine
            key={`pension-${i}`}
            x={m.chart_age ?? m.age}
            stroke={theme.palette.info.main}
            strokeDasharray="6 3"
            label={{
              value: m.person ? `Pension (${m.person})` : 'Pension',
              position: 'top',
              fill: theme.palette.info.main,
              fontSize: 10,
              offset: i * 14,
            }}
          />
        ))}

        {/* Old age pension lines — position at primary person's age on X axis */}
        {oldAgeMilestones.map((m, i) => (
          <ReferenceLine
            key={`oldage-${i}`}
            x={m.chart_age ?? m.age}
            stroke={theme.palette.text.secondary}
            strokeDasharray="3 3"
            label={{
              value: m.person ? `Soc. Sec. (${m.person})` : 'Soc. Sec.',
              position: 'top',
              fill: theme.palette.text.secondary,
              fontSize: 10,
              offset: i * 14,
            }}
          />
        ))}

        <Area
          type="monotone"
          dataKey="nw"
          stroke={theme.palette.primary.main}
          fill="url(#nwGradient)"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />

        {/* Min NW point */}
        <ReferenceDot
          x={minNwAge}
          y={minNw}
          r={5}
          fill={theme.palette.error.main}
          stroke="white"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
