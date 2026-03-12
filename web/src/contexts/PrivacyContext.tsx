import React, { createContext, useCallback, useContext, useState } from 'react'

interface PrivacyContextValue {
  maskBalances: boolean
  toggleMask: () => void
}

const PrivacyContext = createContext<PrivacyContextValue>({ maskBalances: false, toggleMask: () => {} })

export function PrivacyProvider({ children }: { children: React.ReactNode }) {
  const [maskBalances, setMask] = useState(() => localStorage.getItem('mask_balances') === 'true')

  const toggleMask = useCallback(() => {
    setMask((prev) => {
      const next = !prev
      localStorage.setItem('mask_balances', String(next))
      return next
    })
  }, [])

  return <PrivacyContext.Provider value={{ maskBalances, toggleMask }}>{children}</PrivacyContext.Provider>
}

export const usePrivacy = () => useContext(PrivacyContext)
