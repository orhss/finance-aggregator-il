import React, { useCallback, useEffect, useState } from 'react'
import Autocomplete from '@mui/material/Autocomplete'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Chip from '@mui/material/Chip'
import Grid from '@mui/material/Grid2'
import IconButton from '@mui/material/IconButton'
import Slider from '@mui/material/Slider'
import Tab from '@mui/material/Tab'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import Tabs from '@mui/material/Tabs'
import MenuItem from '@mui/material/MenuItem'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import Alert from '@mui/material/Alert'
import CircularProgress from '@mui/material/CircularProgress'
import DeleteIcon from '@mui/icons-material/Delete'
import AddIcon from '@mui/icons-material/Add'
import SearchIcon from '@mui/icons-material/Search'
import { useTheme } from '@mui/material/styles'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useDividendSummary, useDripCompare, usePortfolioIncome, useTickerSearch } from '@/api/dividends'
import { MetricCard } from '@/components/cards/MetricCard'
import { CHART_COLORS } from '@/utils/constants'
import type { DripCompareResponse, HoldingRequest, PortfolioIncome, TickerSearchResult } from '@/types/dividends'

function TabPanel({ value, index, children }: { value: number; index: number; children: React.ReactNode }) {
  return value === index ? <Box sx={{ pt: 2 }}>{children}</Box> : null
}

// ─── Ticker Autocomplete ───

function useDebounce(value: string, delay: number) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}

function TickerAutocomplete({
  onSelect,
  label = 'Search ticker',
  sx,
}: {
  onSelect: (symbol: string) => void
  label?: string
  sx?: object
}) {
  const [inputValue, setInputValue] = useState('')
  const debouncedQuery = useDebounce(inputValue, 300)
  const { data: options, isFetching } = useTickerSearch(debouncedQuery)

  return (
    <Autocomplete
      freeSolo
      options={options ?? []}
      getOptionLabel={(opt) => (typeof opt === 'string' ? opt : `${opt.symbol} — ${opt.name}`)}
      filterOptions={(x) => x}
      loading={isFetching}
      inputValue={inputValue}
      onInputChange={(_, val) => setInputValue(val)}
      onChange={(_, val) => {
        if (!val) return
        const symbol = typeof val === 'string' ? val.toUpperCase() : val.symbol
        onSelect(symbol)
        setInputValue('')
      }}
      renderOption={(props, opt) => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { key, ...rest } = props as React.HTMLAttributes<HTMLLIElement> & { key: string }
        return (
          <li key={key} {...rest}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', gap: 1 }}>
              <Box>
                <Typography variant="body2" fontWeight={600}>{(opt as TickerSearchResult).symbol}</Typography>
                <Typography variant="caption" color="text.secondary" noWrap sx={{ maxWidth: 220, display: 'block' }}>
                  {(opt as TickerSearchResult).name}
                </Typography>
              </Box>
              <Chip
                label={(opt as TickerSearchResult).type}
                size="small"
                variant="outlined"
                sx={{ alignSelf: 'center', fontSize: 10 }}
              />
            </Box>
          </li>
        )
      }}
      renderInput={(params) => (
        <TextField
          {...params}
          size="small"
          label={label}
          placeholder="e.g. AAPL, SCHD, O"
          InputProps={{
            ...params.InputProps,
            startAdornment: <SearchIcon fontSize="small" sx={{ mr: 0.5, color: 'text.secondary' }} />,
          }}
        />
      )}
      sx={{ width: 320, ...sx }}
    />
  )
}

// ─── Ticker Lookup ───

function TickerLookup() {
  const [ticker, setTicker] = useState<string | null>(null)
  const { data, isLoading, error } = useDividendSummary(ticker)
  const theme = useTheme()

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <TickerAutocomplete onSelect={(s) => setTicker(s)} label="Lookup ticker" />

      {isLoading && <CircularProgress size={24} />}
      {error && <Alert severity="error">{(error as Error).message}</Alert>}

      {data && (
        <>
          <Grid container spacing={2}>
            <Grid size={{ xs: 6, md: 3 }}>
              <MetricCard title="Price" value={`${data.currency === 'USD' ? '$' : '₪'}${data.current_price}`} />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <MetricCard
                title="Dividend Yield"
                value={`${data.dividend_yield}%`}
                color={data.dividend_yield >= 3 ? 'success.main' : undefined}
              />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <MetricCard
                title="Annual Dividend"
                value={`${data.currency === 'USD' ? '$' : '₪'}${data.annual_dividend.toFixed(2)}`}
                subtitle={`${data.payment_frequency}x / year`}
              />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <MetricCard
                title="Div Growth (5yr)"
                value={data.growth_rate_5y != null ? `${data.growth_rate_5y}%` : 'N/A'}
                subtitle={data.growth_rate_all != null ? `All-time: ${data.growth_rate_all}%` : undefined}
                color={data.growth_rate_5y != null && data.growth_rate_5y > 0 ? 'success.main' : undefined}
              />
            </Grid>
          </Grid>

          <Card>
            <CardContent>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                {data.name} ({data.ticker}) — Dividend History
              </Typography>
              {data.history.length === 0 ? (
                <Typography color="text.secondary">No dividend history available</Typography>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart
                    data={data.history.map((d) => ({
                      date: d.ex_date,
                      amount: d.amount,
                    }))}
                    margin={{ top: 4, right: 8, left: -16, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 10, fill: theme.palette.text.secondary }}
                      tickLine={false}
                      axisLine={false}
                      interval="preserveStartEnd"
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => `$${v.toFixed(2)}`}
                    />
                    <Tooltip
                      contentStyle={{
                        background: theme.palette.background.paper,
                        border: `1px solid ${theme.palette.divider}`,
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                      formatter={(v: number) => [`$${v.toFixed(4)}`, 'Dividend']}
                    />
                    <Bar dataKey="amount" fill={CHART_COLORS[0]} radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </Box>
  )
}

// ─── DRIP Calculator ───

interface TickerConfig {
  ticker: string
  divGrowth: string  // '' = auto/historical
  priceGrowth: number
  sharePrice: string  // '' = use current market price
}

function DripCalculator() {
  const [tickerConfigs, setTickerConfigs] = useState<TickerConfig[]>([
    { ticker: 'SCHD', divGrowth: '', priceGrowth: 7, sharePrice: '' },
  ])
  const [shares, setShares] = useState(100)
  const [annualContribution, setAnnualContribution] = useState(0)
  const [taxRate, setTaxRate] = useState(0)
  const [years, setYears] = useState(20)

  const drip = useDripCompare()

  const addTicker = useCallback((symbol: string) => {
    if (tickerConfigs.some((t) => t.ticker === symbol)) return
    setTickerConfigs((prev) => [...prev, { ticker: symbol, divGrowth: '', priceGrowth: 7, sharePrice: '' }])
  }, [tickerConfigs])

  const removeTicker = (ticker: string) =>
    setTickerConfigs((prev) => prev.filter((t) => t.ticker !== ticker))

  const updateTicker = (ticker: string, field: keyof Omit<TickerConfig, 'ticker'>, value: string | number) =>
    setTickerConfigs((prev) => prev.map((t) => (t.ticker === ticker ? { ...t, [field]: value } : t)))

  const handleCalculate = () => {
    if (tickerConfigs.length === 0) return
    drip.mutate({
      tickers: tickerConfigs.map((t) => ({
        ticker: t.ticker,
        dividend_growth_rate: t.divGrowth !== '' ? parseFloat(t.divGrowth) : null,
        price_growth_rate: t.priceGrowth,
        share_price_override: t.sharePrice !== '' ? parseFloat(t.sharePrice) : null,
      })),
      initial_shares: shares,
      years,
      annual_contribution: annualContribution,
      dividend_tax_rate: taxRate,
    })
  }

  const data = drip.data

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Card>
        <CardContent>
          <Typography variant="subtitle2" fontWeight={600} gutterBottom>
            DRIP Projection Settings
          </Typography>

          {/* Tickers table with per-ticker growth rates */}
          <Table size="small" sx={{ mb: 2 }}>
            <TableHead>
              <TableRow>
                <TableCell>Ticker</TableCell>
                <TableCell align="right" sx={{ width: 120 }}>Share Price $</TableCell>
                <TableCell align="right" sx={{ width: 120 }}>Div Growth %</TableCell>
                <TableCell align="right" sx={{ width: 120 }}>Price Growth %</TableCell>
                <TableCell sx={{ width: 40 }} />
              </TableRow>
            </TableHead>
            <TableBody>
              {tickerConfigs.map((t, i) => (
                <TableRow key={t.ticker}>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Box
                        sx={{
                          width: 10,
                          height: 10,
                          borderRadius: '50%',
                          bgcolor: CHART_COLORS[i % CHART_COLORS.length],
                          flexShrink: 0,
                        }}
                      />
                      <Typography variant="body2" fontWeight={600}>{t.ticker}</Typography>
                    </Box>
                  </TableCell>
                  <TableCell align="right">
                    <TextField
                      size="small"
                      variant="standard"
                      type="number"
                      placeholder="Current"
                      value={t.sharePrice}
                      onChange={(e) => updateTicker(t.ticker, 'sharePrice', e.target.value)}
                      sx={{ width: 80 }}
                      inputProps={{ style: { textAlign: 'right' } }}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <TextField
                      size="small"
                      variant="standard"
                      type="number"
                      placeholder="Auto"
                      value={t.divGrowth}
                      onChange={(e) => updateTicker(t.ticker, 'divGrowth', e.target.value)}
                      sx={{ width: 80 }}
                      inputProps={{ style: { textAlign: 'right' } }}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <TextField
                      size="small"
                      variant="standard"
                      type="number"
                      value={t.priceGrowth}
                      onChange={(e) => updateTicker(t.ticker, 'priceGrowth', Number(e.target.value))}
                      sx={{ width: 80 }}
                      inputProps={{ style: { textAlign: 'right' } }}
                    />
                  </TableCell>
                  <TableCell>
                    <IconButton size="small" onClick={() => removeTicker(t.ticker)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <TickerAutocomplete onSelect={addTicker} label="Add ticker to compare" />

          <Grid container spacing={2} sx={{ mt: 2 }}>
            <Grid size={{ xs: 6, md: 4 }}>
              <TextField
                label="Initial Shares (each)"
                size="small"
                fullWidth
                type="number"
                value={shares}
                onChange={(e) => setShares(Number(e.target.value))}
              />
            </Grid>
            <Grid size={{ xs: 6, md: 4 }}>
              <TextField
                label="Annual Contribution ($)"
                size="small"
                fullWidth
                type="number"
                value={annualContribution}
                onChange={(e) => setAnnualContribution(Number(e.target.value))}
              />
            </Grid>
            <Grid size={{ xs: 6, md: 4 }}>
              <TextField
                label="Dividend Tax Rate (%)"
                size="small"
                fullWidth
                type="number"
                value={taxRate}
                onChange={(e) => setTaxRate(Number(e.target.value))}
                inputProps={{ min: 0, max: 100, step: 1 }}
              />
            </Grid>
          </Grid>
          <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ minWidth: 80 }}>
              Years: {years}
            </Typography>
            <Slider
              value={years}
              onChange={(_, v) => setYears(v as number)}
              min={5}
              max={40}
              step={5}
              marks
              sx={{ maxWidth: 300 }}
            />
            <Button variant="contained" onClick={handleCalculate} disabled={drip.isPending || tickerConfigs.length === 0}>
              {drip.isPending ? <CircularProgress size={20} /> : 'Compare'}
            </Button>
          </Box>
        </CardContent>
      </Card>

      {drip.isError && <Alert severity="error">{(drip.error as Error).message}</Alert>}

      {data && <DripCompareResults data={data} />}
    </Box>
  )
}

function DripCompareResults({ data }: { data: DripCompareResponse }) {
  const theme = useTheme()
  const valid = data.results.filter((r) => !r.error)
  const [breakdownTicker, setBreakdownTicker] = useState(valid[0]?.ticker ?? '')

  // Build merged chart data: { year, SCHD_value, O_value, ... }
  const valueChartData = React.useMemo(() => {
    if (valid.length === 0) return []
    const years = valid[0].points.length
    return Array.from({ length: years }, (_, i) => {
      const row: Record<string, number> = { year: i }
      valid.forEach((r) => {
        if (i < r.points.length) {
          row[`${r.ticker}_value`] = r.points[i].portfolio_value
          row[`${r.ticker}_income`] = r.points[i].annual_dividend_income
        }
      })
      return row
    })
  }, [valid])

  return (
    <>
      {/* Summary stats per ticker */}
      {valid.map((r, i) => (
        <Card key={r.ticker} sx={{ borderLeft: 3, borderColor: CHART_COLORS[i % CHART_COLORS.length] }}>
          <CardContent sx={{ pb: '12px !important' }}>
            <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, mb: 1.5 }}>
              <Typography variant="subtitle1" fontWeight={700}>{r.ticker}</Typography>
              <Typography variant="body2" color="text.secondary">{r.name}</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
                ${r.initial_share_price}/share
              </Typography>
            </Box>
            <Grid container spacing={1.5}>
              <Grid size={{ xs: 4, md: 2 }}>
                <Typography variant="caption" color="text.secondary">Ending Balance</Typography>
                <Typography variant="body1" fontWeight={600}>${r.ending_balance.toLocaleString()}</Typography>
              </Grid>
              <Grid size={{ xs: 4, md: 2 }}>
                <Typography variant="caption" color="text.secondary">Total Return</Typography>
                <Typography variant="body1" fontWeight={600} color={r.total_return_pct >= 0 ? 'success.main' : 'error.main'}>
                  {r.total_return_pct.toFixed(1)}%
                </Typography>
              </Grid>
              <Grid size={{ xs: 4, md: 2 }}>
                <Typography variant="caption" color="text.secondary">Avg Annual Return</Typography>
                <Typography variant="body1" fontWeight={600}>{r.avg_annual_return_pct.toFixed(2)}%</Typography>
              </Grid>
              <Grid size={{ xs: 4, md: 2 }}>
                <Typography variant="caption" color="text.secondary">Annual Income</Typography>
                <Typography variant="body1" fontWeight={600}>${r.final_annual_income.toLocaleString()}</Typography>
                {r.total_tax_paid > 0 && (
                  <Typography variant="caption" color="text.secondary">
                    After tax: ${r.final_annual_income_after_tax.toLocaleString()}
                  </Typography>
                )}
              </Grid>
              <Grid size={{ xs: 4, md: 2 }}>
                <Typography variant="caption" color="text.secondary">Total Dividends</Typography>
                <Typography variant="body1" fontWeight={600}>${r.total_dividends_paid.toLocaleString()}</Typography>
                {r.total_tax_paid > 0 && (
                  <Typography variant="caption" color="error.main">
                    Tax paid: ${r.total_tax_paid.toLocaleString()}
                  </Typography>
                )}
              </Grid>
              <Grid size={{ xs: 4, md: 2 }}>
                <Typography variant="caption" color="text.secondary">Yield on Cost</Typography>
                <Typography variant="body1" fontWeight={600} color="success.main">{r.yield_on_cost.toFixed(2)}%</Typography>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      ))}

      {/* Errors */}
      {data.results.filter((r) => r.error).map((r) => (
        <Alert key={r.ticker} severity="error">{r.ticker}: {r.error}</Alert>
      ))}

      {/* Overlaid charts */}
      {valid.length > 0 && (
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Portfolio Value Growth
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={valueChartData} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                    <defs>
                      {valid.map((r, i) => (
                        <linearGradient key={r.ticker} id={`cmpGrad-${i}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={0.15} />
                          <stop offset="95%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={0.02} />
                        </linearGradient>
                      ))}
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
                    <XAxis
                      dataKey="year"
                      tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                    />
                    <Tooltip
                      contentStyle={{
                        background: theme.palette.background.paper,
                        border: `1px solid ${theme.palette.divider}`,
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                      formatter={(v: number, name: string) => [
                        `$${v.toLocaleString()}`,
                        name.replace('_value', ''),
                      ]}
                    />
                    <Legend
                      wrapperStyle={{ fontSize: 11 }}
                      formatter={(value: string) => value.replace('_value', '')}
                    />
                    {valid.map((r, i) => (
                      <Area
                        key={r.ticker}
                        type="monotone"
                        dataKey={`${r.ticker}_value`}
                        stroke={CHART_COLORS[i % CHART_COLORS.length]}
                        fill={`url(#cmpGrad-${i})`}
                        strokeWidth={2}
                      />
                    ))}
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Annual Dividend Income
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={valueChartData} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                    <defs>
                      {valid.map((r, i) => (
                        <linearGradient key={r.ticker} id={`incGrad-${i}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={0.15} />
                          <stop offset="95%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={0.02} />
                        </linearGradient>
                      ))}
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
                    <XAxis
                      dataKey="year"
                      tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => `$${v.toLocaleString()}`}
                    />
                    <Tooltip
                      contentStyle={{
                        background: theme.palette.background.paper,
                        border: `1px solid ${theme.palette.divider}`,
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                      formatter={(v: number, name: string) => [
                        `$${v.toLocaleString()}`,
                        name.replace('_income', ''),
                      ]}
                    />
                    <Legend
                      wrapperStyle={{ fontSize: 11 }}
                      formatter={(value: string) => value.replace('_income', '')}
                    />
                    {valid.map((r, i) => (
                      <Area
                        key={r.ticker}
                        type="monotone"
                        dataKey={`${r.ticker}_income`}
                        stroke={CHART_COLORS[i % CHART_COLORS.length]}
                        fill={`url(#incGrad-${i})`}
                        strokeWidth={2}
                      />
                    ))}
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Year-by-year breakdown */}
      {valid.length > 0 && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1.5 }}>
              <Typography variant="subtitle2" fontWeight={600}>
                Year-by-Year Breakdown
              </Typography>
              {valid.length > 1 && (
                <TextField
                  select
                  size="small"
                  value={breakdownTicker}
                  onChange={(e) => setBreakdownTicker(e.target.value)}
                  sx={{ minWidth: 160 }}
                >
                  {valid.map((r, i) => (
                    <MenuItem key={r.ticker} value={r.ticker}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: CHART_COLORS[i % CHART_COLORS.length] }} />
                        {r.ticker}
                      </Box>
                    </MenuItem>
                  ))}
                </TextField>
              )}
            </Box>
            {(() => {
              const selected = valid.find((r) => r.ticker === breakdownTicker) ?? valid[0]
              if (!selected) return null
              return (
                <Box sx={{ maxHeight: 440, overflow: 'auto' }}>
                  {(() => {
                    const hasTax = selected.points.some((pt) => pt.annual_tax > 0)
                    return (
                      <Table size="small" stickyHeader>
                        <TableHead>
                          <TableRow>
                            <TableCell>Year</TableCell>
                            <TableCell align="right">Shares</TableCell>
                            <TableCell align="right">Price</TableCell>
                            <TableCell align="right">Portfolio Value</TableCell>
                            <TableCell align="right">Dividend</TableCell>
                            {hasTax && <TableCell align="right">Tax</TableCell>}
                            {hasTax && <TableCell align="right">After Tax</TableCell>}
                            <TableCell align="right">Cumul. Divs</TableCell>
                            {hasTax && <TableCell align="right">Cumul. Tax</TableCell>}
                            <TableCell align="right">YoC</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {selected.points.map((pt) => {
                            const yoc = selected.initial_investment > 0
                              ? (pt.annual_dividend_income / selected.initial_investment * 100)
                              : 0
                            return (
                              <TableRow key={pt.year}>
                                <TableCell>{pt.year}</TableCell>
                                <TableCell align="right">{pt.shares.toLocaleString(undefined, { maximumFractionDigits: 2 })}</TableCell>
                                <TableCell align="right">${pt.share_price.toLocaleString()}</TableCell>
                                <TableCell align="right">${pt.portfolio_value.toLocaleString()}</TableCell>
                                <TableCell align="right">${pt.annual_dividend_income.toLocaleString()}</TableCell>
                                {hasTax && <TableCell align="right" sx={{ color: 'error.main' }}>${pt.annual_tax.toLocaleString()}</TableCell>}
                                {hasTax && <TableCell align="right">${pt.annual_dividend_after_tax.toLocaleString()}</TableCell>}
                                <TableCell align="right">${pt.total_dividends_received.toLocaleString()}</TableCell>
                                {hasTax && <TableCell align="right" sx={{ color: 'error.main' }}>${pt.total_tax_paid.toLocaleString()}</TableCell>}
                                <TableCell align="right">{yoc.toFixed(2)}%</TableCell>
                              </TableRow>
                            )
                          })}
                        </TableBody>
                      </Table>
                    )
                  })()}
                </Box>
              )
            })()}
          </CardContent>
        </Card>
      )}
    </>
  )
}

// ─── Portfolio Income ───

function PortfolioIncomePage() {
  const [holdings, setHoldings] = useState<HoldingRequest[]>([
    { ticker: 'SCHD', shares: 100 },
    { ticker: 'O', shares: 50 },
  ])
  const [newTicker, setNewTicker] = useState('')
  const [newShares, setNewShares] = useState('')

  const portfolio = usePortfolioIncome()

  const addHolding = () => {
    if (!newTicker.trim() || !newShares) return
    setHoldings([...holdings, { ticker: newTicker.trim().toUpperCase(), shares: Number(newShares) }])
    setNewTicker('')
    setNewShares('')
  }

  const removeHolding = (i: number) => {
    setHoldings(holdings.filter((_, idx) => idx !== i))
  }

  const handleCalculate = () => {
    if (holdings.length === 0) return
    portfolio.mutate(holdings)
  }

  const data = portfolio.data

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Card>
        <CardContent>
          <Typography variant="subtitle2" fontWeight={600} gutterBottom>
            Portfolio Holdings
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Ticker</TableCell>
                <TableCell align="right">Shares</TableCell>
                <TableCell width={48} />
              </TableRow>
            </TableHead>
            <TableBody>
              {holdings.map((h, i) => (
                <TableRow key={i}>
                  <TableCell>{h.ticker}</TableCell>
                  <TableCell align="right">{h.shares}</TableCell>
                  <TableCell>
                    <IconButton size="small" onClick={() => removeHolding(i)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
              <TableRow>
                <TableCell>
                  <TextField
                    size="small"
                    placeholder="Ticker"
                    value={newTicker}
                    onChange={(e) => setNewTicker(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && addHolding()}
                    variant="standard"
                  />
                </TableCell>
                <TableCell align="right">
                  <TextField
                    size="small"
                    placeholder="Shares"
                    type="number"
                    value={newShares}
                    onChange={(e) => setNewShares(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && addHolding()}
                    variant="standard"
                    sx={{ width: 80 }}
                  />
                </TableCell>
                <TableCell>
                  <IconButton size="small" onClick={addHolding} disabled={!newTicker.trim()}>
                    <AddIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
          <Box sx={{ mt: 2 }}>
            <Button
              variant="contained"
              onClick={handleCalculate}
              disabled={holdings.length === 0 || portfolio.isPending}
            >
              {portfolio.isPending ? <CircularProgress size={20} /> : 'Calculate Income'}
            </Button>
          </Box>
        </CardContent>
      </Card>

      {portfolio.isError && <Alert severity="error">{(portfolio.error as Error).message}</Alert>}

      {data && <PortfolioResults data={data} />}
    </Box>
  )
}

function PortfolioResults({ data }: { data: PortfolioIncome }) {
  const theme = useTheme()
  const validHoldings = data.holdings.filter((h) => !h.error)

  return (
    <>
      <Grid container spacing={2}>
        <Grid size={{ xs: 6, md: 4 }}>
          <MetricCard title="Total Annual Income" value={`$${data.total_annual_income.toLocaleString()}`} color="success.main" />
        </Grid>
        <Grid size={{ xs: 6, md: 4 }}>
          <MetricCard title="Portfolio Value" value={`$${data.total_portfolio_value.toLocaleString()}`} />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <MetricCard
            title="Weighted Yield"
            value={`${data.weighted_yield}%`}
            subtitle={`$${(data.total_annual_income / 12).toFixed(0)}/month`}
          />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                Income by Holding
              </Typography>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  data={validHoldings.map((h) => ({ name: h.ticker, income: h.annual_income ?? 0 }))}
                  layout="vertical"
                  margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
                  <XAxis
                    type="number"
                    tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                    tickFormatter={(v) => `$${v}`}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                    width={60}
                  />
                  <Tooltip
                    contentStyle={{
                      background: theme.palette.background.paper,
                      border: `1px solid ${theme.palette.divider}`,
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                    formatter={(v: number) => [`$${v.toLocaleString()}`, 'Annual Income']}
                  />
                  <Bar dataKey="income" fill={CHART_COLORS[2]} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                Holdings Detail
              </Typography>
              <Box sx={{ maxHeight: 280, overflow: 'auto' }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Ticker</TableCell>
                      <TableCell align="right">Shares</TableCell>
                      <TableCell align="right">Yield</TableCell>
                      <TableCell align="right">Income/yr</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data.holdings.map((h) => (
                      <TableRow key={h.ticker}>
                        <TableCell>
                          <Typography variant="body2" fontWeight={600}>
                            {h.ticker}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {h.name}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">{h.shares}</TableCell>
                        <TableCell align="right">
                          {h.error ? (
                            <Chip label="Error" size="small" color="error" variant="outlined" />
                          ) : (
                            `${h.yield_pct}%`
                          )}
                        </TableCell>
                        <TableCell align="right">
                          {h.error ? '—' : `$${(h.annual_income ?? 0).toLocaleString()}`}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </>
  )
}

// ─── Main Page ───

export default function Dividends() {
  const [tab, setTab] = useState(0)

  return (
    <Box>
      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        variant="scrollable"
        scrollButtons="auto"
        sx={{ mb: 1, borderBottom: 1, borderColor: 'divider' }}
      >
        <Tab label="Ticker Lookup" />
        <Tab label="DRIP Calculator" />
        <Tab label="Portfolio Income" />
      </Tabs>

      <TabPanel value={tab} index={0}>
        <TickerLookup />
      </TabPanel>
      <TabPanel value={tab} index={1}>
        <DripCalculator />
      </TabPanel>
      <TabPanel value={tab} index={2}>
        <PortfolioIncomePage />
      </TabPanel>
    </Box>
  )
}
