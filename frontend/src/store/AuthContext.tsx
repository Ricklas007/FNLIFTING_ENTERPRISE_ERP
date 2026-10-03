import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, tokenStore } from '@/services/api'
import { AuthContext } from '@/store/auth-context'
import type { User } from '@/types'

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
