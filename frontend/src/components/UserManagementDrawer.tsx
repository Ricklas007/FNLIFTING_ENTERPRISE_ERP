import { useEffect, useMemo, useState } from 'react'
import { Check, Clock3, RefreshCw, Search, ShieldCheck, UserCog, Users, X } from 'lucide-react'
import { api, ApiError } from '@/services/api'
import type { User } from '@/types'
import { cn } from '@/lib/utils'

export function UserManagementDrawer({ onClose }: { onClose: () => void }) {
  const [users, setUsers] = useState<User[]>([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true); setError(null)
    try { setUsers(await api.users()) }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Falha ao carregar utilizadores.') }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [])

  async function approve(user: User) {
    setWorking(user.id); setError(null)
    try { await api.approveUser(user.id); await load() }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Falha ao aprovar conta.') }
    finally { setWorking(null) }
  }

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase()
    return users.filter(user => !term || `${user.full_name} ${user.email} ${user.username}`.toLowerCase().includes(term))
  }, [users, query])
  const pending = users.filter(user => user.status === 'pending').length

  return (
    <div className="drawer-layer" role="dialog" aria-modal="true" aria-label="Gestão de utilizadores e permissões">
      <button className="drawer-backdrop" onClick={onClose} aria-label="Fechar" />
      <aside className="user-drawer">
        <header className="drawer-head">
          <div className="drawer-title-icon"><UserCog /></div>
          <div><span>Administração do sistema</span><h2>Utilizadores & RBAC</h2></div>
          <button onClick={onClose} aria-label="Fechar painel"><X /></button>
        </header>
        <div className="drawer-summary">
          <div><span><Users /></span><p><strong>{users.length}</strong> contas registadas</p></div>
          <div><span className="pending"><Clock3 /></span><p><strong>{pending}</strong> a aguardar aprovação</p></div>
          <div><span><ShieldCheck /></span><p><strong>15</strong> perfis configurados</p></div>
        </div>
        <div className="drawer-toolbar">
          <label><Search /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Pesquisar utilizador..." /></label>
          <button onClick={load} disabled={loading}><RefreshCw className={loading ? 'animate-spin' : ''} /></button>
        </div>
        {error && <div className="drawer-error">{error}</div>}
        <div className="users-list">
          {loading && !users.length ? <div className="drawer-loading"><span className="button-spinner" />A carregar acessos...</div> : filtered.map(user => (
            <article className="user-row" key={user.id}>
              <span className="user-row-avatar">{user.full_name.split(' ').slice(0,2).map(part => part[0]).join('').toUpperCase()}</span>
              <div className="user-row-identity"><strong>{user.full_name}</strong><small>{user.email} · @{user.username}</small><em>{user.company.name}</em></div>
              <div className="user-row-role"><span>{user.roles[0]?.display_name ?? 'Perfil solicitado'}</span><small>{user.permissions.includes('*') ? 'Acesso total' : `${user.permissions.length} permissões`}</small></div>
              <span className={cn('status-badge', user.status)}>{user.status === 'active' ? 'Ativo' : user.status === 'pending' ? 'Pendente' : user.status}</span>
              {user.status === 'pending' ? (
                <button className="approve-button" onClick={() => approve(user)} disabled={working === user.id}>{working === user.id ? <RefreshCw className="animate-spin" /> : <Check />} Aprovar</button>
              ) : <span className="approved-icon"><ShieldCheck /></span>}
            </article>
          ))}
          {!loading && !filtered.length && <div className="empty-users">Nenhum utilizador corresponde à pesquisa.</div>}
        </div>
        <footer className="drawer-footer"><ShieldCheck /> As alterações de acesso são validadas pela API e associadas à empresa do utilizador.</footer>
      </aside>
    </div>
  )
}
