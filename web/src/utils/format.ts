/**
 * Formatting utilities — ported from streamlit_app/utils/formatters.py
 */

export function formatCurrency(amount: number | null | undefined, currency = '₪'): string {
  if (amount == null) return 'N/A'
  const abs = Math.abs(amount)
  const formatted = abs.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return amount < 0 ? `-${currency}${formatted}` : `${currency}${formatted}`
}

export function formatAmount(amount: number | null | undefined, masked = false): string {
  if (masked) return '••••••'
  return formatCurrency(amount)
}

export function formatDate(dateStr: string | null | undefined, format = 'short'): string {
  if (!dateStr) return 'N/A'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr

  if (format === 'short') {
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
  }
  return d.toLocaleDateString()
}

export function formatRelativeDate(dateStr: string | null | undefined): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const today = new Date()
  const diff = Math.floor((today.getTime() - d.getTime()) / 86400000)

  if (diff === 0) return 'Today'
  if (diff === 1) return 'Yesterday'
  if (diff < 7) return `${diff} days ago`
  return formatDate(dateStr)
}

export function formatRelativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return 'Never'
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  const diffHr = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHr / 24)

  if (diffMin < 1) return 'Just now'
  if (diffMin < 60) return `${diffMin} min ago`
  if (diffHr < 24) return `${diffHr} hr ago`
  if (diffDay === 1) return 'Yesterday'
  if (diffDay < 7) return `${diffDay} days ago`
  return formatDate(dateStr, 'short')
}

export function formatNumber(num: number | null | undefined, decimals = 0): string {
  if (num == null) return 'N/A'
  return num.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

export function formatPercentage(value: number | null | undefined, decimals = 1): string {
  if (value == null) return 'N/A'
  return `${value.toFixed(decimals)}%`
}

export function formatInstitution(institution: string): string {
  const map: Record<string, string> = {
    cal: 'CAL',
    max: 'Max',
    isracard: 'Isracard',
    excellence: 'Excellence',
    meitav: 'Meitav',
    migdal: 'Migdal',
    phoenix: 'Phoenix',
  }
  return map[institution.toLowerCase()] ?? institution
}

export function amountColor(amount: number, mode: 'light' | 'dark' = 'light'): string {
  if (amount > 0) return mode === 'light' ? '#16a34a' : '#34d399'
  if (amount < 0) return mode === 'light' ? '#dc2626' : '#f87171'
  return mode === 'light' ? '#6b7280' : '#64748b'
}

/** Format large ILS values for chart axes (e.g. ₪1.2M, ₪500K) */
export function formatAxisValue(v: number): string {
  const abs = Math.abs(v)
  if (abs >= 1_000_000) return `₪${(v / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000) return `₪${(v / 1_000).toFixed(0)}K`
  return `₪${v.toFixed(0)}`
}

/** Format month number (1-12) to abbreviated name */
export function monthName(month: number): string {
  return new Date(2000, month - 1, 1).toLocaleString('en-US', { month: 'short' })
}
