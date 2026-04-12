import React, { useCallback, useMemo, useState } from 'react'
import Box from '@mui/material/Box'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Grid from '@mui/material/Grid2'
import IconButton from '@mui/material/IconButton'
import InputAdornment from '@mui/material/InputAdornment'
import LinearProgress from '@mui/material/LinearProgress'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import EditIcon from '@mui/icons-material/Edit'
import CheckIcon from '@mui/icons-material/Check'
import { useTheme } from '@mui/material/styles'
import {
  Line,
  LineChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from 'recharts'
import { formatCurrency } from '@/utils/format'
import type { PortfolioProgression } from '@/types/balance'

const TARGET_KEY = 'fi_retirement_target'
const SPENDING_KEY = 'fi_monthly_spending'
const DEFAULT_TARGET = 10_000_000
const DEFAULT_SPENDING = 25_000

function getStored(key: string, fallback: number): number {
  const stored = localStorage.getItem(key)
  return stored ? Number(stored) : fallback
}

interface Props {
  data: PortfolioProgression
  height?: number
}

function EditableValue({
  label,
  value,
  onSave,
}: {
  label: string
  value: number
  onSave: (v: number) => void
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')

  const start = useCallback(() => {
    setDraft(String(value))
    setEditing(true)
  }, [value])

  const commit = useCallback(() => {
    const val = Number(draft.replace(/,/g, ''))
    if (val > 0) onSave(val)
    setEditing(false)
  }, [draft, onSave])

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
      <Typography variant="body2" color="text.secondary">
        {label}:
      </Typography>
      {editing ? (
        <TextField
          size="small"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && commit()}
          autoFocus
          sx={{ width: 140 }}
          slotProps={{
            input: {
              startAdornment: <InputAdornment position="start">₪</InputAdornment>,
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton size="small" onClick={commit}>
                    <CheckIcon fontSize="small" />
                  </IconButton>
                </InputAdornment>
              ),
            },
          }}
        />
      ) : (
        <>
          <Typography variant="body2" fontWeight={600}>
            {formatCurrency(value)}
          </Typography>
          <IconButton size="small" onClick={start}>
            <EditIcon sx={{ fontSize: 14 }} />
          </IconButton>
        </>
      )}
    </Box>
  )
}

function MetricProgress({
  title,
  value,
  subtitle,
  progress,
  color,
}: {
  title: string
  value: string
  subtitle?: string
  progress?: number
  color?: string
}) {
  const theme = useTheme()
  return (
    <Card variant="outlined">
      <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
        <Typography variant="caption" color="text.secondary">
          {title}
        </Typography>
        <Typography variant="h5" fontWeight={700} sx={{ color: color ?? 'text.primary' }}>
          {value}
        </Typography>
        {subtitle && (
          <Typography variant="caption" color="text.secondary">
            {subtitle}
          </Typography>
        )}
        {progress != null && (
          <LinearProgress
            variant="determinate"
            value={Math.min(Math.max(progress, 0), 100)}
            sx={{
              mt: 0.5,
              height: 4,
              borderRadius: 2,
              bgcolor: theme.palette.action.hover,
              '& .MuiLinearProgress-bar': {
                borderRadius: 2,
                bgcolor: color ?? 'primary.main',
              },
            }}
          />
        )}
      </CardContent>
    </Card>
  )
}

export function FIProgressChart({ data, height = 320 }: Props) {
  const theme = useTheme()
  const [target, setTarget] = useState(() => getStored(TARGET_KEY, DEFAULT_TARGET))
  const [monthlySpending, setMonthlySpending] = useState(() => getStored(SPENDING_KEY, DEFAULT_SPENDING))

  const saveTarget = useCallback((v: number) => {
    localStorage.setItem(TARGET_KEY, String(v))
    setTarget(v)
  }, [])

  const saveSpending = useCallback((v: number) => {
    localStorage.setItem(SPENDING_KEY, String(v))
    setMonthlySpending(v)
  }, [])

  const chartData = useMemo(() => {
    if (!data.points.length) return []

    const pensionSeries = data.series_names.filter(
      (s) => s.toLowerCase().includes('pension')
    )

    const liquidByDate = new Map<string, number>()
    const totalByDate = new Map<string, number>()
    for (const p of data.points) {
      totalByDate.set(p.date, (totalByDate.get(p.date) ?? 0) + p.total_amount)
      if (!pensionSeries.includes(p.series)) {
        liquidByDate.set(p.date, (liquidByDate.get(p.date) ?? 0) + p.total_amount)
      }
    }

    const sortedDates = Array.from(totalByDate.keys()).sort()
    const years = new Set(sortedDates.map((d) => new Date(d).getFullYear()))
    const multiYear = years.size > 1
    const dateFmt: Intl.DateTimeFormatOptions = multiYear
      ? { month: 'short', year: '2-digit' }
      : { month: 'short', day: 'numeric' }

    return sortedDates.map((d) => {
      const liquid = liquidByDate.get(d) ?? 0
      const total = totalByDate.get(d) ?? 0
      return {
        date: new Date(d).toLocaleDateString('en-US', dateFmt),
        liquidPct: (liquid / target) * 100,
        totalPct: (total / target) * 100,
      }
    })
  }, [data, target])

  const last = chartData.length ? chartData[chartData.length - 1] : null
  const currentLiquidPct = last?.liquidPct ?? 0
  const currentTotalPct = last?.totalPct ?? 0

  // Derive amounts from percentages
  const currentLiquid = (currentLiquidPct / 100) * target
  const currentTotal = (currentTotalPct / 100) * target

  // Withdrawal rate = (monthly * 12) / liquid assets
  const withdrawalRate = currentLiquid > 0 ? ((monthlySpending * 12) / currentLiquid) * 100 : null
  // Safe withdrawal rate is typically 3-4%
  const wrColor = withdrawalRate == null ? undefined
    : withdrawalRate <= 4 ? theme.palette.success.main
    : withdrawalRate <= 6 ? theme.palette.warning.main
    : theme.palette.error.main
  // Invert for progress: 4% = 100%, 8% = 50%, 12% = 33%
  const wrProgress = withdrawalRate != null ? Math.min((4 / withdrawalRate) * 100, 100) : undefined

  // Runway = liquid / monthly
  const runwayMonths = monthlySpending > 0 ? currentLiquid / monthlySpending : null
  const runwayYears = runwayMonths != null ? Math.floor(runwayMonths / 12) : null
  const runwayRemMonths = runwayMonths != null ? Math.round(runwayMonths % 12) : null
  // Progress: assume 30 years (360 months) = 100%
  const runwayProgress = runwayMonths != null ? Math.min((runwayMonths / 360) * 100, 100) : undefined

  if (!chartData.length) {
    return (
      <Box sx={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography color="text.secondary">No investment data</Typography>
      </Box>
    )
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* Settings row */}
      <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
        <EditableValue label="Target" value={target} onSave={saveTarget} />
        <EditableValue label="Monthly expenses" value={monthlySpending} onSave={saveSpending} />
      </Box>

      {/* Metric cards */}
      <Grid container spacing={2}>
        <Grid size={{ xs: 6, md: 3 }}>
          <MetricProgress
            title="FI Progress (Liquid)"
            value={`${currentLiquidPct.toFixed(1)}%`}
            subtitle={`${formatCurrency(currentLiquid)} of ${formatCurrency(target)}`}
            progress={currentLiquidPct}
            color={theme.palette.primary.main}
          />
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <MetricProgress
            title="FI Progress (Total)"
            value={`${currentTotalPct.toFixed(1)}%`}
            subtitle={`${formatCurrency(currentTotal)} of ${formatCurrency(target)}`}
            progress={currentTotalPct}
            color={theme.palette.warning.main}
          />
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <MetricProgress
            title="Withdrawal Rate"
            value={withdrawalRate != null ? `${withdrawalRate.toFixed(1)}%` : '—'}
            subtitle={withdrawalRate != null ? (withdrawalRate <= 4 ? 'Safe (≤4%)' : withdrawalRate <= 6 ? 'Moderate' : 'High (>6%)') : undefined}
            progress={wrProgress}
            color={wrColor}
          />
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <MetricProgress
            title="Runway"
            value={runwayYears != null ? `${runwayYears}y ${runwayRemMonths}m` : '—'}
            subtitle={runwayMonths != null ? `${Math.round(runwayMonths)} months` : undefined}
            progress={runwayProgress}
            color={theme.palette.info.main}
          />
        </Grid>
      </Grid>

      {/* Line chart */}
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
            tickFormatter={(v) => `${v.toFixed(0)}%`}
          />
          <Tooltip
            formatter={(value: number, name: string) => {
              if (name === 'liquidPct') return [`${value.toFixed(1)}%`, 'Liquid']
              if (name === 'totalPct') return [`${value.toFixed(1)}%`, 'With Pension']
              return [String(value), name]
            }}
            contentStyle={{
              background: theme.palette.background.paper,
              border: `1px solid ${theme.palette.divider}`,
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <ReferenceLine
            y={100}
            stroke={theme.palette.success.main}
            strokeDasharray="6 3"
            label={{
              value: '100%',
              position: 'right',
              fill: theme.palette.success.main,
              fontSize: 11,
            }}
          />
          <Line
            type="monotone"
            dataKey="totalPct"
            name="totalPct"
            stroke={theme.palette.warning.main}
            strokeWidth={1.5}
            strokeDasharray="6 3"
            dot={false}
            activeDot={{ r: 3 }}
          />
          <Line
            type="monotone"
            dataKey="liquidPct"
            name="liquidPct"
            stroke={theme.palette.primary.main}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </Box>
  )
}
