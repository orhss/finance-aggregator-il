import React, { useMemo, useState } from 'react'
import Box from '@mui/material/Box'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableContainer from '@mui/material/TableContainer'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import ToggleButton from '@mui/material/ToggleButton'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import Typography from '@mui/material/Typography'
import type { MonthlyRow, SimulationSummary } from '@/types/retirement'

interface Props {
  monthly: MonthlyRow[]
  summary: SimulationSummary
  persons: string[]
}

interface AggRow {
  label: string
  age: number
  expenses: number
  portfolioWithdrawal: number
  khWithdrawal: number
  pensionIncome: number
  socialSecurity: number
  salary: number
  taxes: number
  net: number
}

function fmt(v: number): string {
  if (Math.abs(v) < 1) return '—'
  const abs = Math.abs(v)
  if (abs >= 1_000_000) return `${v < 0 ? '-' : ''}₪${(abs / 1_000_000).toFixed(1)}M`
  if (abs >= 10_000) return `${v < 0 ? '-' : ''}₪${(abs / 1_000).toFixed(0)}k`
  return `₪${Math.round(v).toLocaleString()}`
}

function cellColor(v: number): string | undefined {
  if (Math.abs(v) < 1) return undefined
  return v > 0 ? 'success.main' : 'error.main'
}

export function CashflowTable({ monthly, summary, persons }: Props) {
  const [mode, setMode] = useState<'yearly' | 'monthly'>('yearly')

  const fireMonth = summary.fire_month_index

  const rows = useMemo(() => {
    const postFire = monthly.filter((r) => r.month >= fireMonth)
    if (!postFire.length) return []

    if (mode === 'monthly') {
      // Show first 24 months then every 12th month
      const selected: MonthlyRow[] = []
      for (let i = 0; i < postFire.length; i++) {
        if (i < 24 || i % 12 === 0 || i === postFire.length - 1) {
          selected.push(postFire[i])
        }
      }
      return selected.map((r): AggRow => {
        const pension = r.pension_mukeret.reduce((s, v) => s + v, 0) + r.pension_mazka.reduce((s, v) => s + v, 0)
        const social = r.old_age.reduce((s, v) => s + v, 0)
        const kh = r.withdrawal_kh.reduce((s, v) => s + v, 0)
        const taxes = r.income_tax.reduce((s, v) => s + v, 0) + r.bituach_leumi.reduce((s, v) => s + v, 0) + r.portfolio_tax
        const totalIn = r.income + r.withdrawal_portfolio + kh + pension + social
        const totalOut = r.expenses + taxes
        return {
          label: r.date,
          age: Math.floor(r.age),
          expenses: -r.expenses,
          portfolioWithdrawal: r.withdrawal_portfolio,
          khWithdrawal: kh,
          pensionIncome: pension,
          socialSecurity: social,
          salary: r.income,
          taxes: -taxes,
          net: totalIn - totalOut,
        }
      })
    }

    // Yearly: group by year
    const byYear = new Map<string, MonthlyRow[]>()
    for (const r of postFire) {
      const year = r.date.split('-')[0]
      if (!byYear.has(year)) byYear.set(year, [])
      byYear.get(year)!.push(r)
    }

    return Array.from(byYear.entries()).map(([year, rows]): AggRow => {
      const sum = (fn: (r: MonthlyRow) => number) => rows.reduce((s, r) => s + fn(r), 0)
      const pension = sum((r) => r.pension_mukeret.reduce((s, v) => s + v, 0) + r.pension_mazka.reduce((s, v) => s + v, 0))
      const social = sum((r) => r.old_age.reduce((s, v) => s + v, 0))
      const kh = sum((r) => r.withdrawal_kh.reduce((s, v) => s + v, 0))
      const taxes = sum((r) => r.income_tax.reduce((s, v) => s + v, 0) + r.bituach_leumi.reduce((s, v) => s + v, 0) + r.portfolio_tax)
      const expenses = sum((r) => r.expenses)
      const salary = sum((r) => r.income)
      const portfolio = sum((r) => r.withdrawal_portfolio)
      const totalIn = salary + portfolio + kh + pension + social
      const totalOut = expenses + taxes
      return {
        label: year,
        age: Math.floor(rows[0].age),
        expenses: -expenses,
        portfolioWithdrawal: portfolio,
        khWithdrawal: kh,
        pensionIncome: pension,
        socialSecurity: social,
        salary: salary,
        taxes: -taxes,
        net: totalIn - totalOut,
      }
    })
  }, [monthly, fireMonth, mode])

  if (!rows.length) {
    return (
      <Box sx={{ py: 4, textAlign: 'center' }}>
        <Typography color="text.secondary">No post-FIRE data</Typography>
      </Box>
    )
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
        <ToggleButtonGroup
          value={mode}
          exclusive
          size="small"
          onChange={(_, v) => v && setMode(v)}
        >
          <ToggleButton value="yearly">Yearly</ToggleButton>
          <ToggleButton value="monthly">Monthly</ToggleButton>
        </ToggleButtonGroup>
      </Box>
      <TableContainer sx={{ maxHeight: 500 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>{mode === 'yearly' ? 'Year' : 'Month'}</TableCell>
              <TableCell align="right">Age</TableCell>
              <TableCell align="right">Salary</TableCell>
              <TableCell align="right">Portfolio</TableCell>
              <TableCell align="right">KH</TableCell>
              <TableCell align="right">Pension</TableCell>
              <TableCell align="right">Soc. Sec.</TableCell>
              <TableCell align="right">Expenses</TableCell>
              <TableCell align="right">Taxes</TableCell>
              <TableCell align="right">Net</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.label} hover>
                <TableCell sx={{ fontWeight: 500 }}>{r.label}</TableCell>
                <TableCell align="right">{r.age}</TableCell>
                <TableCell align="right" sx={{ color: r.salary > 0 ? 'success.main' : undefined }}>
                  {fmt(r.salary)}
                </TableCell>
                <TableCell align="right" sx={{ color: r.portfolioWithdrawal > 0 ? 'info.main' : undefined }}>
                  {fmt(r.portfolioWithdrawal)}
                </TableCell>
                <TableCell align="right" sx={{ color: r.khWithdrawal > 0 ? 'info.main' : undefined }}>
                  {fmt(r.khWithdrawal)}
                </TableCell>
                <TableCell align="right" sx={{ color: r.pensionIncome > 0 ? 'success.main' : undefined }}>
                  {fmt(r.pensionIncome)}
                </TableCell>
                <TableCell align="right" sx={{ color: r.socialSecurity > 0 ? 'success.main' : undefined }}>
                  {fmt(r.socialSecurity)}
                </TableCell>
                <TableCell align="right" sx={{ color: 'error.main' }}>
                  {fmt(r.expenses)}
                </TableCell>
                <TableCell align="right" sx={{ color: r.taxes < -1 ? 'error.main' : undefined }}>
                  {fmt(r.taxes)}
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 600, color: cellColor(r.net) }}>
                  {fmt(r.net)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}
