import React from 'react'
import Box from '@mui/material/Box'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableContainer from '@mui/material/TableContainer'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import Typography from '@mui/material/Typography'
import Chip from '@mui/material/Chip'
import { useTheme } from '@mui/material/styles'
import { formatAxisValue } from '@/utils/format'
import type { Scenario, ScenarioResult, SimulationSummary } from '@/types/retirement'

interface Props {
  scenarios: Scenario[]
  allResults: Record<number, ScenarioResult>
  onSelectScenario: (id: number) => void
}

type MetricRow = {
  label: string
  getValue: (s: SimulationSummary, status: string) => string
  /** 'lower' = smaller is better, 'higher' = larger is better, 'none' = no comparison */
  best: 'lower' | 'higher' | 'none'
  getRaw: (s: SimulationSummary) => number | null
}

function formatAge(age: number, dateStr: string): string {
  const [y, m] = dateStr.split('-')
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const monthName = months[parseInt(m, 10) - 1] || m
  return `${age.toFixed(1)} (${monthName} ${y})`
}

const METRICS: MetricRow[] = [
  {
    label: 'Status',
    getValue: (_, status) => (status === 'success' ? 'Success' : 'Impossible'),
    best: 'none',
    getRaw: () => null,
  },
  {
    label: 'FIRE Age',
    getValue: (s) => formatAge(s.fire_age, s.fire_date),
    best: 'lower',
    getRaw: (s) => s.fire_age,
  },
  {
    label: 'Years to FIRE',
    getValue: (s) => `${s.years_to_fire.toFixed(1)} years`,
    best: 'lower',
    getRaw: (s) => s.years_to_fire,
  },
  {
    label: 'Withdrawal Rate',
    getValue: (s) => {
      const label = s.withdrawal_rate_at_fire <= 4 ? 'Safe' : s.withdrawal_rate_at_fire <= 6 ? 'Moderate' : 'High'
      return `${s.withdrawal_rate_at_fire.toFixed(1)}% (${label})`
    },
    best: 'lower',
    getRaw: (s) => s.withdrawal_rate_at_fire,
  },
  {
    label: 'Min Net Worth',
    getValue: (s) => `${formatAxisValue(s.min_nw)} at age ${s.min_nw_age.toFixed(0)}`,
    best: 'higher',
    getRaw: (s) => s.min_nw,
  },
  {
    label: 'End Net Worth',
    getValue: (s) => `${formatAxisValue(s.end_nw)} at age ${s.end_age.toFixed(0)}`,
    best: 'higher',
    getRaw: (s) => s.end_nw,
  },
  {
    label: 'Portfolio Depletes',
    getValue: (s) => (s.portfolio_depletion_age != null ? `Age ${s.portfolio_depletion_age}` : 'Never'),
    best: 'higher',
    // "Never" is best → treat null as Infinity so higher wins
    getRaw: (s) => s.portfolio_depletion_age ?? Infinity,
  },
]

export function ScenarioCompare({ scenarios, allResults, onSelectScenario }: Props) {
  const theme = useTheme()

  // Only scenarios with ok results participate in best-value comparisons
  const okEntries = scenarios
    .map((s) => ({ id: s.id, result: allResults[s.id] }))
    .filter((e): e is { id: number; result: Extract<ScenarioResult, { status: 'ok' }> } => e.result?.status === 'ok')

  // Compute best value per metric
  const bestIds: Record<string, Set<number>> = {}
  for (const metric of METRICS) {
    if (metric.best === 'none') continue
    const values = okEntries.map((e) => ({
      id: e.id,
      raw: metric.getRaw(e.result.data.summary),
    })).filter((v) => v.raw !== null) as { id: number; raw: number }[]
    if (values.length < 2) continue

    const bestVal = metric.best === 'lower'
      ? Math.min(...values.map((v) => v.raw))
      : Math.max(...values.map((v) => v.raw))
    bestIds[metric.label] = new Set(values.filter((v) => v.raw === bestVal).map((v) => v.id))
  }

  return (
    <TableContainer>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell sx={{ fontWeight: 600, minWidth: 140 }}>Metric</TableCell>
            {scenarios.map((s) => (
              <TableCell
                key={s.id}
                align="center"
                sx={{
                  fontWeight: 600,
                  cursor: 'pointer',
                  '&:hover': { color: 'primary.main' },
                  minWidth: 150,
                }}
                onClick={() => onSelectScenario(s.id)}
              >
                {s.name}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {METRICS.map((metric) => (
            <TableRow key={metric.label}>
              <TableCell sx={{ fontWeight: 500, color: 'text.secondary' }}>{metric.label}</TableCell>
              {scenarios.map((s) => {
                const r = allResults[s.id]
                if (!r) {
                  return (
                    <TableCell key={s.id} align="center">
                      <Typography variant="body2" color="text.disabled">
                        Not run
                      </Typography>
                    </TableCell>
                  )
                }
                if (r.status === 'error') {
                  // Show error only in the Status row, blank for others
                  if (metric.label === 'Status') {
                    return (
                      <TableCell key={s.id} align="center">
                        <Chip label="Error" size="small" color="error" variant="outlined" />
                      </TableCell>
                    )
                  }
                  return (
                    <TableCell key={s.id} align="center">
                      <Typography variant="body2" color="text.disabled">—</Typography>
                    </TableCell>
                  )
                }

                const isBest = bestIds[metric.label]?.has(s.id)
                const value = metric.getValue(r.data.summary, r.data.status)

                // Status row: chip styling
                if (metric.label === 'Status') {
                  const isImpossible = r.data.status === 'impossible'
                  return (
                    <TableCell key={s.id} align="center">
                      <Chip
                        label={value}
                        size="small"
                        color={isImpossible ? 'warning' : 'success'}
                        variant="outlined"
                      />
                    </TableCell>
                  )
                }

                return (
                  <TableCell
                    key={s.id}
                    align="center"
                    sx={{
                      fontWeight: isBest ? 600 : 400,
                      color: isBest ? theme.palette.success.main : 'text.primary',
                    }}
                  >
                    {value}
                  </TableCell>
                )
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {/* Error details below the table */}
      {scenarios.map((s) => {
        const r = allResults[s.id]
        if (r?.status !== 'error') return null
        return (
          <Box key={s.id} sx={{ mt: 1, px: 2 }}>
            <Typography variant="caption" color="error">
              {s.name}: {r.message}
            </Typography>
          </Box>
        )
      })}
    </TableContainer>
  )
}
