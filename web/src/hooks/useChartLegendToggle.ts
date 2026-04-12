import { useCallback, useState } from 'react'

/**
 * Manages legend click-to-hide/show for Recharts multi-series charts.
 * Returns the hidden set and a click handler to pass to <Legend onClick={...} />.
 */
export function useChartLegendToggle() {
  const [hidden, setHidden] = useState<Set<string>>(new Set())

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleLegendClick = useCallback((e: any) => {
    const series = String(e.dataKey || e.value)
    if (!series) return
    setHidden((prev) => {
      const next = new Set(prev)
      if (next.has(series)) next.delete(series)
      else next.add(series)
      return next
    })
  }, [])

  return { hidden, handleLegendClick }
}
