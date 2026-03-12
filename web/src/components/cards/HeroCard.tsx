import React from 'react'
import Box from '@mui/material/Box'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Skeleton from '@mui/material/Skeleton'
import Typography from '@mui/material/Typography'
import { useTheme } from '@mui/material/styles'
import { AmountDisplay } from '@/components/common/AmountDisplay'
import { useAccountSummary } from '@/api/accounts'
import { monthName } from '@/utils/format'

export function HeroCard() {
  const { data, isLoading } = useAccountSummary()
  const theme = useTheme()
  const now = new Date()

  if (isLoading) {
    return (
      <Card sx={{ background: theme.palette.primary.main, color: 'white' }}>
        <CardContent sx={{ py: 3 }}>
          <Skeleton variant="text" width="40%" sx={{ bgcolor: 'rgba(255,255,255,0.3)' }} />
          <Skeleton variant="text" height={60} width="60%" sx={{ bgcolor: 'rgba(255,255,255,0.3)' }} />
          <Box sx={{ display: 'flex', gap: 4, mt: 2 }}>
            <Skeleton variant="text" width={80} sx={{ bgcolor: 'rgba(255,255,255,0.3)' }} />
            <Skeleton variant="text" width={80} sx={{ bgcolor: 'rgba(255,255,255,0.3)' }} />
          </Box>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card
      sx={{
        background: `linear-gradient(135deg, ${theme.palette.primary.dark} 0%, ${theme.palette.primary.main} 60%, ${theme.palette.secondary.main} 100%)`,
        color: 'white',
      }}
    >
      <CardContent sx={{ py: 3 }}>
        <Typography variant="caption" sx={{ opacity: 0.8, textTransform: 'uppercase', letterSpacing: 1 }}>
          Total Portfolio · {monthName(now.getMonth())} {now.getFullYear()}
        </Typography>

        <AmountDisplay
          amount={data?.total_balance ?? null}
          variant="h4"
          sx={{ fontWeight: 800, color: 'white', mt: 0.5 }}
          showColor={false}
        />

        <Box sx={{ display: 'flex', gap: 4, mt: 2 }}>
          <Box>
            <Typography variant="caption" sx={{ opacity: 0.7 }}>
              Accounts
            </Typography>
            <Typography variant="h6" fontWeight={600}>
              {data?.total_accounts ?? '—'}
            </Typography>
          </Box>
          {Object.entries(data?.by_type ?? {}).slice(0, 2).map(([type, count]) => (
            <Box key={type}>
              <Typography variant="caption" sx={{ opacity: 0.7, textTransform: 'capitalize' }}>
                {type.replace('_', ' ')}
              </Typography>
              <Typography variant="h6" fontWeight={600}>
                {count}
              </Typography>
            </Box>
          ))}
        </Box>
      </CardContent>
    </Card>
  )
}
