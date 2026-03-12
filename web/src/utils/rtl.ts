/**
 * RTL utilities — ported from streamlit_app/utils/rtl.py
 */

/** Returns true if the string contains Hebrew characters */
export function hasHebrew(text: string): boolean {
  return /[\u0590-\u05FF]/.test(text)
}

/** Determines appropriate text direction for mixed content */
export function textDir(text: string): 'rtl' | 'ltr' {
  return hasHebrew(text) ? 'rtl' : 'ltr'
}

/** Clean up merchant name whitespace */
export function cleanMerchantName(merchant: string | null | undefined): string {
  if (!merchant) return 'Unknown'
  return merchant.trim().replace(/\s+/g, ' ')
}
