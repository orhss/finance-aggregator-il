import React from 'react'
import Grid from '@mui/material/Grid2'
import { MetricCard } from '@/components/cards/MetricCard'
import { formatAxisValue } from '@/utils/format'
import type { SimulationSummary } from '@/types/retirement'

interface Props {
  summary: SimulationSummary
  impossible: boolean
}

function formatAge(age: number, dateStr: string): string {
  const [y, m] = dateStr.split('-')
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const monthName = months[parseInt(m, 10) - 1] || m
  return `${age.toFixed(1)} (${monthName} ${y})`
}


function wrColor(rate: number): string | undefined {
  if (rate <= 4) return 'success.main'
  if (rate <= 6) return 'warning.main'
  return 'error.main'
}

export function ResultsOverview({ summary, impossible }: Props) {
  return (
    <Grid container spacing={2}>
      <Grid size={{ xs: 6, md: 3 }}>
        <MetricCard
          title="FIRE Age"
          value={formatAge(summary.fire_age, summary.fire_date)}
          color={impossible ? 'warning.main' : 'primary.main'}
        />
      </Grid>
      <Grid size={{ xs: 6, md: 3 }}>
        <MetricCard
          title="Years to FIRE"
          value={`${summary.years_to_fire.toFixed(1)} years`}
          color="primary.main"
        />
      </Grid>
      <Grid size={{ xs: 6, md: 3 }}>
        <MetricCard
          title="Min Net Worth"
          value={formatAxisValue(summary.min_nw)}
          subtitle={`at age ${summary.min_nw_age.toFixed(0)}`}
          color={summary.min_nw < 0 ? 'error.main' : summary.min_nw < 100_000 ? 'warning.main' : undefined}
        />
      </Grid>
      <Grid size={{ xs: 6, md: 3 }}>
        <MetricCard
          title="End Net Worth"
          value={formatAxisValue(summary.end_nw)}
          subtitle={`at age ${summary.end_age.toFixed(0)}`}
          color="success.main"
        />
      </Grid>
      <Grid size={{ xs: 6, md: 3 }}>
        <MetricCard
          title="Portfolio Depletes"
          value={summary.portfolio_depletion_age != null ? `Age ${summary.portfolio_depletion_age}` : 'Never'}
          color={summary.portfolio_depletion_age != null ? 'info.main' : 'success.main'}
        />
      </Grid>
      <Grid size={{ xs: 6, md: 3 }}>
        <MetricCard
          title="Withdrawal Rate"
          value={`${summary.withdrawal_rate_at_fire.toFixed(1)}%`}
          subtitle={summary.withdrawal_rate_at_fire <= 4 ? 'Safe' : summary.withdrawal_rate_at_fire <= 6 ? 'Moderate' : 'High'}
          color={wrColor(summary.withdrawal_rate_at_fire)}
        />
      </Grid>
    </Grid>
  )
}
