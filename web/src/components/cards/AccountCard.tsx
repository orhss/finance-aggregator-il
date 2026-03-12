import React from 'react'
import Box from '@mui/material/Box'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Chip from '@mui/material/Chip'
import Typography from '@mui/material/Typography'
import { AmountDisplay } from '@/components/common/AmountDisplay'
import { formatRelativeDate } from '@/utils/format'
import type { Account } from '@/types/account'

const INSTITUTION_LABELS: Record<string, string> = {
  cal: 'CAL',
  max: 'Max',
  isracard: 'Isracard',
  excellence: 'Excellence',
  migdal: 'Migdal',
  phoenix: 'Phoenix',
}

const TYPE_ICONS: Record<string, string> = {
  credit_card: '💳',
  broker: '📈',
  pension: '🏦',
  savings: '💰',
}

interface AccountCardProps {
  account: Account
  onClick?: (account: Account) => void
}

export function AccountCard({ account, onClick }: AccountCardProps) {
  const icon = TYPE_ICONS[account.account_type] ?? '🏦'
  const label = INSTITUTION_LABELS[account.institution] ?? account.institution
  const balance = account.latest_balance?.total_amount ?? null

  return (
    <Card
      variant="outlined"
      sx={{ cursor: onClick ? 'pointer' : 'default' }}
      onClick={() => onClick?.(account)}
    >
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography fontSize={20}>{icon}</Typography>
            <Box>
              <Typography variant="subtitle2" fontWeight={600} noWrap>
                {account.account_name || account.account_number}
              </Typography>
              <Chip label={label} size="small" sx={{ height: 18, fontSize: '0.65rem', mt: 0.25 }} />
            </Box>
          </Box>
          {balance != null && (
            <AmountDisplay amount={balance} variant="subtitle1" sx={{ fontWeight: 700 }} showColor={false} />
          )}
        </Box>

        {account.account_number && account.account_name && (
          <Typography variant="caption" color="text.secondary" display="block">
            {account.account_number}
          </Typography>
        )}

        {account.last_synced_at && (
          <Typography variant="caption" color="text.secondary">
            Synced {formatRelativeDate(account.last_synced_at)}
          </Typography>
        )}
      </CardContent>
    </Card>
  )
}
