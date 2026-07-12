import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, tokenStore } from '@/services/api'
import type { MFARequiredResponse, User } from '@/types'

interface AuthContextValue {
  user: User | null
  checking: boolean
  login: (identifier: string, password: string, portal: 'staff' | 'client', remember: boolean) => Promise<MFARequiredResponse | void>
  completeMfaLogin: (challengeId: string, code: string, remember: boolean) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    const token = tokenStore.access()
    if (!token) {
      setChecking(false)
      return
    }
    api.me().then(setUser).catch(() => tokenStore.clear()).finally(() => setChecking(false))
  }, [])

  const login = useCallback(async (identifier: string, password: string, portal: 'staff' | 'client', remember: boolean) => {
    const response = await api.login({ identifier, password, portal, remember_me: remember })
    if ('mfa_required' in response) return response
    tokenStore.save(response, remember)
    setUser(response.user)
  }, [])

  const completeMfaLogin = useCallback(async (challengeId: string, code: string, remember: boolean) => {
    const response = await api.verifyMfaLogin({ challenge_id: challengeId, code, remember_me: remember })
    tokenStore.save(response, remember)
    setUser(response.user)
  }, [])

  const logout = useCallback(async () => {
    try { await api.logout() } catch { /* The local token must still be removed. */ }
    tokenStore.clear()
    setUser(null)
  }, [])

  const value = useMemo(() => ({ user, checking, login, completeMfaLogin, logout }), [user, checking, login, completeMfaLogin, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
