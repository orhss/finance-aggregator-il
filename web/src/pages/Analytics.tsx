import React, { useMemo, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Grid from '@mui/material/Grid2'
import Tab from '@mui/material/Tab'
import Tabs from '@mui/material/Tabs'
import ToggleButton from '@mui/material/ToggleButton'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
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
import {
  useCategoryBreakdown,
  useCategoryTrends,
  useMonthlyTrends,
  useMonthlySummary,
  useTagBreakdown,
} from '@/api/analytics'
import { useAccountSummary } from '@/api/accounts'
import type { AccountSummary } from '@/types/account'
import { usePortfolioByType, usePortfolioByAccount, usePnLSummary } from '@/api/balances'
import { useBudgetProgress } from '@/api/budget'
import { AccountGrowthLines } from '@/components/charts/AccountGrowthLines'
import { CategoryBars } from '@/components/charts/CategoryBars'
import { MonthlyTrend } from '@/components/charts/MonthlyTrend'
import { PnLBars } from '@/components/charts/PnLBars'
import { PortfolioProgression } from '@/components/charts/PortfolioProgression'
import { SpendingDonut } from '@/components/charts/SpendingDonut'
import { MetricCard } from '@/components/cards/MetricCard'
import { AmountDisplay } from '@/components/common/AmountDisplay'
import { ChartSkeleton } from '@/components/common/LoadingSkeleton'
import type { CategoryBreakdownItem } from '@/types/analytics'

type PeriodKey = '3m' | '6m' | '1y' | 'all'

function periodToDateRange(period: PeriodKey): { from_date?: string; to_date?: string } {
  if (period === 'all') return {}
  const now = new Date()
  const from = new Date(now)
  if (period === '3m') from.setMonth(from.getMonth() - 3)
  else if (period === '6m') from.setMonth(from.getMonth() - 6)
  else from.setFullYear(from.getFullYear() - 1)
  return { from_date: from.toISOString().slice(0, 10) }
}

const MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const STACK_COLORS = ['#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b']

function TabPanel({ value, index, children }: { value: number; index: number; children: React.ReactNode }) {
  return value === index ? <Box sx={{ pt: 2 }}>{children}</Box> : null
}

function recordToBreakdown(rec: Record<string, number>): CategoryBreakdownItem[] {
  return Object.entries(rec)
    .map(([category, total_amount]) => ({ category, total_amount, count: 0, avg_amount: 0 }))
    .filter((d) => d.total_amount > 0)
    .sort((a, b) => b.total_amount - a.total_amount)
}

const TAG_CHART_DEFAULT_LIMIT = 15

export default function Analytics() {
  const [tab, setTab] = useState(0)
  const [portfolioPeriod, setPortfolioPeriod] = useState<PeriodKey>('1y')
  const [showAllTags, setShowAllTags] = useState(false)
  const [showAllCats, setShowAllCats] = useState(false)
  const theme = useTheme()

  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth() + 1
  const prevYear = month === 1 ? year - 1 : year
  const prevMonth = month === 1 ? 12 : month - 1

  const { data: trends, isLoading: trendsLoading } = useMonthlyTrends({ months: 12 })
  const { data: categories, isLoading: catLoading } = useCategoryBreakdown()
  const { data: tags, isLoading: tagsLoading } = useTagBreakdown()
  const { data: catTrends, isLoading: catTrendsLoading } = useCategoryTrends({ months: 6, top_n: 5 })
  const { data: currentMonth, isLoading: currentLoading } = useMonthlySummary(year, month)
  const { data: lastMonth, isLoading: lastLoading } = useMonthlySummary(prevYear, prevMonth)
  const { data: budget } = useBudgetProgress()
  const { data: accountSummary, isLoading: accountLoading } = useAccountSummary()

  // Pivot category trends data for Recharts: { period, cat1, cat2, ... }[]
  const catTrendsChartData = React.useMemo(() => {
    if (!catTrends) return []
    const cats = Object.keys(catTrends.categories)
    const allPeriods = new Set<string>()
    cats.forEach((cat) => {
      catTrends.categories[cat].forEach(({ year: y, month: m }) => {
        allPeriods.add(`${y}-${String(m).padStart(2, '0')}`)
      })
    })
    return Array.from(allPeriods)
      .sort()
      .map((p) => {
        const [y, m] = p.split('-').map(Number)
        const row: Record<string, string | number> = { period: `${MONTH_ABBR[m - 1]} ${String(y).slice(2)}` }
        cats.forEach((cat) => {
          const pt = catTrends.categories[cat].find((x) => x.year === y && x.month === m)
          row[cat] = pt ? Math.abs(pt.amount) : 0
        })
        return row
      })
  }, [catTrends])

  const catTrendsKeys = catTrends ? Object.keys(catTrends.categories) : []

  // MoM
  const currentSpend = currentMonth ? Math.abs(currentMonth.total_amount) : null
  const lastSpend = lastMonth ? Math.abs(lastMonth.total_amount) : null
  const momPct =
    currentSpend != null && lastSpend && lastSpend > 0
      ? ((currentSpend - lastSpend) / lastSpend) * 100
      : null

  // Tags adapted to CategoryBreakdownItem for CategoryBars
  const tagsAsBars: CategoryBreakdownItem[] = (tags ?? []).map((t) => ({
    category: t.tag,
    total_amount: Math.abs(t.total_amount),
    count: t.count,
    avg_amount: t.count > 0 ? Math.abs(t.total_amount) / t.count : 0,
  }))

  return (
    <Box>
      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        variant="scrollable"
        scrollButtons="auto"
        sx={{ mb: 1, borderBottom: 1, borderColor: 'divider' }}
      >
        <Tab label="Trends" />
        <Tab label="Categories" />
        <Tab label="Tags" />
        <Tab label="Portfolio" />
      </Tabs>

      {/* ── Trends ── */}
      <TabPanel value={tab} index={0}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* MoM row */}
          <Grid container spacing={2}>
            <Grid size={{ xs: 6, md: 3 }}>
              <MetricCard
                title="This Month"
                loading={currentLoading}
                value={currentSpend != null ? <AmountDisplay amount={currentSpend} variant="h5" /> : '—'}
              />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <MetricCard
                title="Last Month"
                loading={lastLoading}
                value={lastSpend != null ? <AmountDisplay amount={lastSpend} variant="h5" /> : '—'}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <MetricCard
                title="vs Last Month"
                loading={currentLoading || lastLoading}
                value={momPct != null ? `${momPct > 0 ? '+' : ''}${momPct.toFixed(1)}%` : '—'}
                color={
                  momPct == null ? undefined : momPct > 5 ? 'error.main' : momPct < -5 ? 'success.main' : undefined
                }
              />
            </Grid>
          </Grid>

          {/* Monthly bar */}
          <Card>
            <CardContent>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                Monthly Spending (12 months)
              </Typography>
              {trendsLoading ? (
                <ChartSkeleton height={260} />
              ) : (
                <MonthlyTrend
                  data={trends ?? []}
                  showBudgetLine={!!budget?.budget}
                  budget={budget?.budget ?? null}
                />
              )}
            </CardContent>
          </Card>

          {/* Category stacked area */}
          <Card>
            <CardContent>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                Top Categories Over Time
              </Typography>
              {catTrendsLoading ? (
                <ChartSkeleton height={260} />
              ) : catTrendsChartData.length === 0 ? (
                <Box sx={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Typography color="text.secondary">No data</Typography>
                </Box>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart data={catTrendsChartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                    <defs>
                      {catTrendsKeys.map((cat, i) => (
                        <linearGradient key={cat} id={`catGrad-${i}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={STACK_COLORS[i % STACK_COLORS.length]} stopOpacity={0.4} />
                          <stop offset="95%" stopColor={STACK_COLORS[i % STACK_COLORS.length]} stopOpacity={0.05} />
                        </linearGradient>
                      ))}
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
                    <XAxis
                      dataKey="period"
                      tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => `₪${(v / 1000).toFixed(0)}k`}
                    />
                    <Tooltip
                      contentStyle={{
                        background: theme.palette.background.paper,
                        border: `1px solid ${theme.palette.divider}`,
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    {catTrendsKeys.map((cat, i) => (
                      <Area
                        key={cat}
                        type="monotone"
                        dataKey={cat}
                        stackId="1"
                        stroke={STACK_COLORS[i % STACK_COLORS.length]}
                        fill={`url(#catGrad-${i})`}
                        strokeWidth={2}
                      />
                    ))}
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </Box>
      </TabPanel>

      {/* ── Categories ── */}
      <TabPanel value={tab} index={1}>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Spending Distribution
                </Typography>
                {catLoading ? <ChartSkeleton height={260} /> : <SpendingDonut data={categories ?? []} />}
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Top Categories
                </Typography>
                {catLoading ? <ChartSkeleton height={260} /> : (
                  <>
                    <CategoryBars
                      data={categories ?? []}
                      limit={showAllCats ? (categories ?? []).length : TAG_CHART_DEFAULT_LIMIT}
                      height={Math.max(260, Math.min((categories ?? []).length, showAllCats ? (categories ?? []).length : TAG_CHART_DEFAULT_LIMIT) * 36)}
                    />
                    {(categories ?? []).length > TAG_CHART_DEFAULT_LIMIT && (
                      <Button size="small" onClick={() => setShowAllCats((v) => !v)} sx={{ mt: 1 }}>
                        {showAllCats ? 'Show top 15' : `Show all (${(categories ?? []).length})`}
                      </Button>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* ── Tags ── */}
      <TabPanel value={tab} index={2}>
        <Card>
          <CardContent>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Spending by Tag
            </Typography>
            {tagsLoading ? (
              <ChartSkeleton height={260} />
            ) : !tagsAsBars.length ? (
              <Typography color="text.secondary" variant="body2">
                No tags applied yet. Go to Organize → Tags to start tagging transactions.
              </Typography>
            ) : (
              <>
                <CategoryBars
                  data={tagsAsBars}
                  limit={showAllTags ? tagsAsBars.length : TAG_CHART_DEFAULT_LIMIT}
                  height={Math.max(260, Math.min(tagsAsBars.length, showAllTags ? tagsAsBars.length : TAG_CHART_DEFAULT_LIMIT) * 36)}
                />
                {tagsAsBars.length > TAG_CHART_DEFAULT_LIMIT && (
                  <Button size="small" onClick={() => setShowAllTags((v) => !v)} sx={{ mt: 1 }}>
                    {showAllTags ? 'Show top 15' : `Show all (${tagsAsBars.length})`}
                  </Button>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </TabPanel>

      {/* ── Portfolio ── */}
      <PortfolioPanel
        tab={tab}
        portfolioPeriod={portfolioPeriod}
        onPeriodChange={setPortfolioPeriod}
        accountSummary={accountSummary}
        accountLoading={accountLoading}
      />
    </Box>
  )
}

/* ── Portfolio Panel (extracted to keep hooks active across tab switches) ── */

function PortfolioPanel({
  tab,
  portfolioPeriod,
  onPeriodChange,
  accountSummary,
  accountLoading,
}: {
  tab: number
  portfolioPeriod: PeriodKey
  onPeriodChange: (p: PeriodKey) => void
  accountSummary: AccountSummary | undefined
  accountLoading: boolean
}) {
  const dateRange = useMemo(() => periodToDateRange(portfolioPeriod), [portfolioPeriod])
  const { data: byType, isLoading: byTypeLoading } = usePortfolioByType(dateRange)
  const { data: byAccount, isLoading: byAccountLoading } = usePortfolioByAccount(dateRange)
  const { data: pnl, isLoading: pnlLoading } = usePnLSummary()

  const totalPnL = useMemo(() => {
    if (!pnl) return null
    return pnl.reduce((sum, item) => sum + (item.profit_loss ?? 0), 0)
  }, [pnl])

  return (
    <TabPanel value={tab} index={3}>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {/* Metrics row */}
        <Grid container spacing={2}>
          <Grid size={{ xs: 6, md: 4 }}>
            <MetricCard
              title="Total Portfolio"
              loading={accountLoading}
              value={<AmountDisplay amount={accountSummary?.total_balance ?? 0} variant="h5" />}
            />
          </Grid>
          <Grid size={{ xs: 6, md: 4 }}>
            <MetricCard
              title="Active Accounts"
              loading={accountLoading}
              value={accountSummary?.total_accounts ?? '—'}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <MetricCard
              title="Total P&L"
              loading={pnlLoading}
              value={totalPnL != null ? <AmountDisplay amount={totalPnL} variant="h5" /> : '—'}
            />
          </Grid>
        </Grid>

        {/* Period selector */}
        <Box>
          <ToggleButtonGroup
            value={portfolioPeriod}
            exclusive
            onChange={(_, v) => v && onPeriodChange(v as PeriodKey)}
            size="small"
          >
            <ToggleButton value="3m">3M</ToggleButton>
            <ToggleButton value="6m">6M</ToggleButton>
            <ToggleButton value="1y">1Y</ToggleButton>
            <ToggleButton value="all">All</ToggleButton>
          </ToggleButtonGroup>
        </Box>

        {/* Net Worth Progression (stacked area) */}
        <Card>
          <CardContent>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Net Worth Progression
            </Typography>
            {byTypeLoading ? (
              <ChartSkeleton height={300} />
            ) : (
              <PortfolioProgression data={byType ?? { points: [], series_names: [] }} />
            )}
          </CardContent>
        </Card>

        {/* Account Growth + P&L side by side */}
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Account Growth
                </Typography>
                {byAccountLoading ? (
                  <ChartSkeleton height={280} />
                ) : (
                  <AccountGrowthLines data={byAccount ?? { points: [], series_names: [] }} />
                )}
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Current P&L
                </Typography>
                {pnlLoading ? (
                  <ChartSkeleton height={280} />
                ) : (
                  <PnLBars data={pnl ?? []} />
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Donuts at bottom */}
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Balance by Account Type
                </Typography>
                {accountLoading ? (
                  <ChartSkeleton height={260} />
                ) : (
                  <SpendingDonut data={recordToBreakdown(accountSummary?.by_type ?? {})} />
                )}
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Balance by Institution
                </Typography>
                {accountLoading ? (
                  <ChartSkeleton height={260} />
                ) : (
                  <SpendingDonut data={recordToBreakdown(accountSummary?.by_institution ?? {})} />
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    </TabPanel>
  )
}
