import { createContext } from 'react'

import type { MFARequiredResponse, User } from '@/types'

export interface AuthContextValue {
  user: User | null
  checking: boolean
  login: (identifier: string, password: string, portal: 'staff' | 'client', remember: boolean) => Promise<MFARequiredResponse | void>
  completeMfaLogin: (challengeId: string, code: string, remember: boolean) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
