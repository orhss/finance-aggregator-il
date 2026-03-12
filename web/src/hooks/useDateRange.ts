import { useState } from 'react'

type DateRange = { from: string | null; to: string | null }

function toIso(d: Date): string {
  return d.toISOString().split('T')[0]
}

export function useDateRange(defaultMonths = 3) {
  const today = new Date()
  const defaultFrom = new Date(today.getFullYear(), today.getMonth() - defaultMonths, 1)

  const [range, setRange] = useState<DateRange>({
    from: toIso(defaultFrom),
    to: toIso(today),
  })

  const presets = {
    thisMonth: () => {
      const from = new Date(today.getFullYear(), today.getMonth(), 1)
      setRange({ from: toIso(from), to: toIso(today) })
    },
    lastMonth: () => {
      const from = new Date(today.getFullYear(), today.getMonth() - 1, 1)
      const to = new Date(today.getFullYear(), today.getMonth(), 0)
      setRange({ from: toIso(from), to: toIso(to) })
    },
    last3Months: () => {
      const from = new Date(today.getFullYear(), today.getMonth() - 3, 1)
      setRange({ from: toIso(from), to: toIso(today) })
    },
    last6Months: () => {
      const from = new Date(today.getFullYear(), today.getMonth() - 6, 1)
      setRange({ from: toIso(from), to: toIso(today) })
    },
    thisYear: () => {
      const from = new Date(today.getFullYear(), 0, 1)
      setRange({ from: toIso(from), to: toIso(today) })
    },
  }

  return { range, setRange, presets }
}
