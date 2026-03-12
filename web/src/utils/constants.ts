/**
 * Constants — mirrors config/constants.py
 */

export const AccountType = {
  BROKER: 'broker',
  PENSION: 'pension',
  CREDIT_CARD: 'credit_card',
  SAVINGS: 'savings',
} as const

export const Institution = {
  EXCELLENCE: 'excellence',
  MEITAV: 'meitav',
  MIGDAL: 'migdal',
  PHOENIX: 'phoenix',
  CAL: 'cal',
  MAX: 'max',
  ISRACARD: 'isracard',
} as const

export const UnifiedCategory = {
  GROCERIES: 'groceries',
  RESTAURANTS: 'restaurants',
  FUEL: 'fuel',
  TRANSPORTATION: 'transportation',
  UTILITIES: 'utilities',
  HOME: 'home',
  HEALTHCARE: 'healthcare',
  BEAUTY: 'beauty',
  SHOPPING: 'shopping',
  CLOTHING: 'clothing',
  ELECTRONICS: 'electronics',
  CHILDREN: 'children',
  INSURANCE: 'insurance',
  FINANCE: 'finance',
  FEES: 'fees',
  ENTERTAINMENT: 'entertainment',
  TRAVEL: 'travel',
  EVENTS: 'events',
  SUBSCRIPTIONS: 'subscriptions',
  EDUCATION: 'education',
  DONATIONS: 'donations',
  GIFTS: 'gifts',
  SERVICES: 'services',
  OTHER: 'other',
} as const

export const CATEGORY_ICONS: Record<string, string> = {
  groceries: '🛒',
  restaurants: '🍕',
  fuel: '⛽',
  transportation: '🚗',
  utilities: '💡',
  healthcare: '🏥',
  entertainment: '🎬',
  shopping: '🛍️',
  travel: '✈️',
  education: '📚',
  insurance: '🛡️',
  subscriptions: '📺',
  home: '🏠',
  clothing: '👕',
  electronics: '📱',
  gifts: '🎁',
  fees: '💳',
  other: '📋',
  finance: '💰',
  beauty: '💄',
  children: '👶',
  events: '🎪',
  donations: '❤️',
  services: '🔧',
}

export function getCategoryIcon(category: string | null | undefined): string {
  if (!category) return '📋'
  return CATEGORY_ICONS[category.toLowerCase()] ?? '📋'
}
