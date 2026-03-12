import React from 'react'
import Box from '@mui/material/Box'
import Grid from '@mui/material/Grid2'
import Typography from '@mui/material/Typography'
import { useNavigate } from 'react-router-dom'
import { useMonthlySummary, useCategoryBreakdown } from '@/api/analytics'
import { useTransactions } from '@/api/transactions'
import { useUnmappedCategories } from '@/api/categories'
import { AmountDisplay } from '@/components/common/AmountDisplay'
import { AlertCard } from '@/components/cards/AlertCard'
import { BudgetProgressCard } from '@/components/cards/BudgetProgress'
import { HeroCard } from '@/components/cards/HeroCard'
import { MetricCard } from '@/components/cards/MetricCard'
import { TransactionItem } from '@/components/cards/TransactionItem'
import { MetricsSkeleton, TransactionListSkeleton } from '@/components/common/LoadingSkeleton'
import { getCategoryIcon } from '@/utils/constants'
import type { Transaction } from '@/types/transaction'

export default function Dashboard() {
  const navigate = useNavigate()
  const now = new Date()
  const thisYear = now.getFullYear()
  const thisMonth = now.getMonth() + 1
  const lastMonth = thisMonth === 1 ? 12 : thisMonth - 1
  const lastMonthYear = thisMonth === 1 ? thisYear - 1 : thisYear

  const { data: currentMonthData, isLoading: currentLoading } = useMonthlySummary(thisYear, thisMonth)
  const { data: lastMonthData, isLoading: lastLoading } = useMonthlySummary(lastMonthYear, lastMonth)
  const { data: categories } = useCategoryBreakdown()
  const { data: txnsData, isLoading: txnsLoading } = useTransactions({ limit: 7, offset: 0 })
  const { data: unmapped } = useUnmappedCategories()

  const unmappedCount = unmapped?.length ?? 0
  const unmappedTxns = unmapped?.reduce((sum, u) => sum + u.count, 0) ?? 0
  const topCategory = categories?.[0]?.category ?? null
  const statsLoading = currentLoading || lastLoading

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {unmappedCount > 0 && (
        <AlertCard
          severity="warning"
          title="Uncategorized transactions"
          message={`${unmappedCount} categories with ${unmappedTxns} transactions need mapping.`}
          action={{ label: 'Review', onClick: () => navigate('/organize') }}
        />
      )}

      <HeroCard />

      {statsLoading ? (
        <MetricsSkeleton />
      ) : (
        <Grid container spacing={2}>
          <Grid size={{ xs: 6, md: 3 }}>
            <MetricCard
              title="This Month"
              value={
                <AmountDisplay
                  amount={currentMonthData?.total_amount ?? null}
                  variant="h5"
                  sx={{ fontWeight: 700 }}
                />
              }
              icon={<span>💸</span>}
            />
          </Grid>
          <Grid size={{ xs: 6, md: 3 }}>
            <MetricCard
              title="Last Month"
              value={
                <AmountDisplay
                  amount={lastMonthData?.total_amount ?? null}
                  variant="h5"
                  sx={{ fontWeight: 700 }}
                />
              }
              icon={<span>📅</span>}
            />
          </Grid>
          <Grid size={{ xs: 6, md: 3 }}>
            <MetricCard
              title="Transactions"
              value={currentMonthData?.transaction_count ?? '—'}
              subtitle="This month"
              icon={<span>🧾</span>}
            />
          </Grid>
          <Grid size={{ xs: 6, md: 3 }}>
            <MetricCard
              title="Top Category"
              value={topCategory ? `${getCategoryIcon(topCategory)} ${topCategory}` : '—'}
              icon={<span>🏆</span>}
            />
          </Grid>
        </Grid>
      )}

      <BudgetProgressCard />

      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle1" fontWeight={600}>
            Recent Transactions
          </Typography>
          <Typography
            variant="caption"
            color="primary"
            sx={{ cursor: 'pointer' }}
            onClick={() => navigate('/transactions')}
          >
            See all
          </Typography>
        </Box>

        {txnsLoading ? (
          <TransactionListSkeleton rows={5} />
        ) : (
          txnsData?.items.map((txn) => (
            <TransactionItem
              key={txn.id}
              transaction={txn}
              onClick={() => navigate('/transactions')}
            />
          ))
        )}
      </Box>
    </Box>
  )
}
