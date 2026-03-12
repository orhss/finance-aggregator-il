import React from 'react'
import Box from '@mui/material/Box'
import Card from '@mui/material/Card'
import CardActionArea from '@mui/material/CardActionArea'
import Chip from '@mui/material/Chip'
import Typography from '@mui/material/Typography'
import { AmountDisplay } from '@/components/common/AmountDisplay'
import { RtlText } from '@/components/common/RtlText'
import { formatRelativeDate } from '@/utils/format'
import { getCategoryIcon } from '@/utils/constants'
import type { Transaction } from '@/types/transaction'

interface TransactionItemProps {
  transaction: Transaction
  onClick?: (txn: Transaction) => void
}

export function TransactionItem({ transaction, onClick }: TransactionItemProps) {
  const category = transaction.effective_category
  const icon = getCategoryIcon(category)
  const amount = transaction.charged_amount ?? transaction.original_amount

  return (
    <Card variant="outlined" sx={{ mb: 0.5 }}>
      <CardActionArea onClick={() => onClick?.(transaction)} sx={{ px: 2, py: 1.25 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          {/* Category icon */}
          <Box sx={{ fontSize: 22, flexShrink: 0, width: 32, textAlign: 'center' }}>{icon}</Box>

          {/* Description + meta */}
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <RtlText
              text={transaction.description}
              sx={{
                fontSize: '0.875rem',
                fontWeight: 500,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                display: 'block',
              }}
            />
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mt: 0.25 }}>
              <Typography variant="caption" color="text.secondary">
                {formatRelativeDate(transaction.transaction_date)}
              </Typography>
              {category && (
                <Chip label={category} size="small" sx={{ height: 16, fontSize: '0.65rem' }} />
              )}
            </Box>
          </Box>

          {/* Amount */}
          <AmountDisplay amount={amount} variant="body2" sx={{ fontWeight: 600, flexShrink: 0 }} />
        </Box>
      </CardActionArea>
    </Card>
  )
}
