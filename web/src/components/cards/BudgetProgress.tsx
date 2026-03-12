import React from 'react'
import Box from '@mui/material/Box'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import LinearProgress from '@mui/material/LinearProgress'
import Typography from '@mui/material/Typography'
import { useTheme } from '@mui/material/styles'
import { useBudgetProgress } from '@/api/budget'
import { AmountDisplay } from '@/components/common/AmountDisplay'

export function BudgetProgressCard() {
  const { data, isLoading } = useBudgetProgress()
  const theme = useTheme()

  if (isLoading) return null
  if (!data?.budget) return null

  const pct = data.percent ?? 0
  const overBudget = data.is_over_budget ?? false
  const progressColor = overBudget ? theme.palette.error.main : pct > 80 ? theme.palette.warning.main : theme.palette.primary.main

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="subtitle2" fontWeight={600}>
            Monthly Budget
          </Typography>
          <Typography variant="caption" color={overBudget ? 'error' : 'text.secondary'}>
            {pct.toFixed(0)}%{overBudget ? ' — OVER' : ''}
          </Typography>
        </Box>

        <LinearProgress
          variant="determinate"
          value={Math.min(pct, 100)}
          sx={{
            height: 8,
            borderRadius: 4,
            mb: 1.5,
            bgcolor: `${progressColor}20`,
            '& .MuiLinearProgress-bar': { bgcolor: progressColor, borderRadius: 4 },
          }}
        />

        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Spent
            </Typography>
            <AmountDisplay amount={data.spent} variant="subtitle2" />
          </Box>
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="caption" color="text.secondary">
              {overBudget ? 'Over' : 'Remaining'}
            </Typography>
            <AmountDisplay
              amount={data.remaining ? Math.abs(data.remaining) : null}
              variant="subtitle2"
              showColor={false}
            />
          </Box>
          <Box sx={{ textAlign: 'right' }}>
            <Typography variant="caption" color="text.secondary">
              Budget
            </Typography>
            <AmountDisplay amount={data.budget} variant="subtitle2" showColor={false} />
          </Box>
        </Box>
      </CardContent>
    </Card>
  )
}
