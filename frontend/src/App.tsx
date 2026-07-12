import { AuthProvider, useAuth } from '@/store/AuthContext'
import { BootSequence } from '@/components/BootSequence'
import { AuthPage } from '@/pages/AuthPage'
import { EnterpriseApp } from '@/pages/EnterpriseApp'

function Application() {
  const { user, checking } = useAuth()
  if (checking) return <div className="session-check"><span className="button-spinner" /><p>A validar sessão segura...</p></div>
  return user ? <EnterpriseApp /> : <AuthPage />
}

export default function App() {
  return (
    <BootSequence>
      <AuthProvider><Application /></AuthProvider>
    </BootSequence>
  )
}
