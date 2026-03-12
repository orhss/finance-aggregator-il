import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'

interface AuthContextValue {
  isAuthenticated: boolean
  isLoading: boolean
  username: string | null
  setTokens: (accessToken: string, refreshToken: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue>({
  isAuthenticated: false,
  isLoading: true,
  username: null,
  setTokens: () => {},
  logout: () => {},
})

function decodeUsername(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.sub || null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isLoading, setIsLoading] = useState(true)
  const [username, setUsername] = useState<string | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    async function checkAuth() {
      // Check if backend requires authentication
      try {
        const res = await fetch('/api/auth/status')
        if (res.ok) {
          const data = await res.json()
          if (!data.auth_enabled) {
            setIsAuthenticated(true)
            setUsername('anonymous')
            setIsLoading(false)
            return
          }
        }
      } catch {
        // Backend unreachable — fall through to token check
      }

      // Auth is enabled (or status check failed) — check for existing token
      const token = localStorage.getItem('access_token')
      if (token) {
        setIsAuthenticated(true)
        setUsername(decodeUsername(token))
      }
      setIsLoading(false)
    }
    checkAuth()
  }, [])

  const setTokens = useCallback((accessToken: string, refreshToken: string) => {
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('refresh_token', refreshToken)
    setIsAuthenticated(true)
    setUsername(decodeUsername(accessToken))
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setIsAuthenticated(false)
    setUsername(null)
  }, [])

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, username, setTokens, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
