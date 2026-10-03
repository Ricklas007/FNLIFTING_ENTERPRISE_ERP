import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from 'react'
import {
  Activity, BadgeCheck, Bell, Boxes, Building2, ChevronDown, CircleDollarSign,
  ClipboardCheck, Command, FileBarChart, FileClock, FileText, Gauge, Headphones,
  LayoutDashboard, Menu, PackageCheck, PanelLeftClose, PanelLeftOpen, Search,
  Settings, ShieldCheck, Truck, UserCog, Users, WalletCards, X, Network,
} from 'lucide-react'
import { BrandLogo } from '@/components/BrandLogo'
import { UserManagementDrawer } from '@/components/UserManagementDrawer'
import { useAuth } from '@/store/useAuth'
import { api, ApiError } from '@/services/api'
import { cn } from '@/lib/utils'
import type { AppView, EnterpriseNotification } from '@/types'

type Icon = typeof LayoutDashboard
interface NavItem { id: string; label: string; icon: Icon; phase?: number; permission?: string }
interface NavGroup { label: string; items: NavItem[] }

const enterpriseNav: NavGroup[] = [
  { label: 'Visão geral', items: [{ id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard }] },
  { label: 'Operações', items: [
    { id: 'clients', label: 'Clientes', icon: Building2, permission: 'clients.view' },
    { id: 'equipment', label: 'Equipamentos', icon: Boxes, permission: 'equipment.view' }, { id: 'inspections', label: 'Inspeções', icon: ShieldCheck, permission: 'inspections.view' },
    { id: 'certificates', label: 'Certificados', icon: BadgeCheck, permission: 'certificates.view' },
  ] },
  { label: 'Pessoas', items: [
    { id: 'hr', label: 'Recursos Humanos', icon: Users, permission: 'hr.view' }, { id: 'employees', label: 'Trabalhadores', icon: UserCog, permission: 'employees.view' },
    { id: 'daily-reports', label: 'Relatórios diários', icon: FileClock, permission: 'daily_reports.view' },
    { id: 'performance', label: 'Desempenho', icon: Activity, permission: 'performance.view' }, { id: 'departments', label: 'Departamentos', icon: Network, permission: 'departments.view' },
  ] },
  { label: 'Frota & logística', items: [
    { id: 'fleet', label: 'Camiões e motoristas', icon: Truck, permission: 'fleet.view' }, { id: 'trips', label: 'Viagens & GPS', icon: Gauge, permission: 'fleet.view' },
  ] },
  { label: 'Gestão', items: [
    { id: 'finance', label: 'Financeiro', icon: CircleDollarSign, permission: 'finance.view' }, { id: 'assets', label: 'Património', icon: PackageCheck, permission: 'assets.view' },
    { id: 'documents', label: 'Documentos', icon: FileText, permission: 'documents.view' }, { id: 'reports', label: 'Relatórios avançados', icon: FileBarChart, permission: 'reports.view' },
  ] },
  { label: 'Administração', items: [
    { id: 'users-rbac', label: 'Utilizadores & RBAC', icon: UserCog, permission: 'users.manage' }, { id: 'audit', label: 'Auditoria', icon: ShieldCheck, permission: 'audit.view' }, { id: 'sync', label: 'Backup & Sync', icon: Command, permission: 'sync.manage' },
    { id: 'settings', label: 'Configurações', icon: Settings, permission: 'settings.manage' }, { id: 'ops', label: 'Produção & Saúde', icon: Activity, permission: 'settings.manage' },
  ] },
  { label: 'Fases 8-12', items: [
    { id: 'cloud-security', label: 'Cloud & Segurança', icon: Bell, phase: 8, permission: 'dashboard.view' },
    { id: 'fleet-command', label: 'Command Center', icon: Gauge, phase: 9, permission: 'fleet.view' },
    { id: 'ai-automation', label: 'IA & Automação', icon: Command, phase: 10, permission: 'reports.view' },
    { id: 'employee-portal', label: 'RH Enterprise', icon: Users, phase: 11, permission: 'hr.view|daily_reports.submit' },
    { id: 'executive-saas', label: 'BI & SaaS', icon: FileBarChart, phase: 12, permission: 'reports.view' },
  ] },
]

const clientNav: NavGroup[] = [
  { label: 'Portal da empresa', items: [{ id: 'dashboard', label: 'Visão geral', icon: LayoutDashboard }] },
  { label: 'Serviços FNLIFTING', items: [
    { id: 'certificates', label: 'Certificados', icon: BadgeCheck }, { id: 'equipment', label: 'Equipamentos', icon: Boxes },
    { id: 'portal-requests', label: 'Solicitar serviço', icon: ClipboardCheck }, { id: 'portal-billing', label: 'Faturas & recibos', icon: WalletCards },
    { id: 'documents', label: 'Documentos', icon: FileText },
  ] },
]

export function DashboardLayout({ children, activeView, onNavigate }: { children: ReactNode; activeView: AppView; onNavigate: (view: AppView) => void }) {
  const { user, logout } = useAuth()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [userAdminOpen, setUserAdminOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [notifications, setNotifications] = useState<EnterpriseNotification[]>([])
  const [notificationsBusy, setNotificationsBusy] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const searchInput = useRef<HTMLInputElement | null>(null)
  const navigation = user?.account_type === 'external' ? clientNav : enterpriseNav
  const permissionKey = user?.permissions.join('|') ?? ''
  const permissionSet = useMemo(() => new Set(permissionKey ? permissionKey.split('|') : []), [permissionKey])

  const canAccessItem = useCallback((item: NavItem) => {
    if (!item.permission) return true
    const permissions = item.permission.split('|')
    return permissionSet.has('*') || permissions.some(permission => permissionSet.has(permission))
  }, [permissionSet])

  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(null), 3400)
    return () => window.clearTimeout(timer)
  }, [notice])

  const initials = useMemo(() => user?.full_name.split(' ').slice(0, 2).map(word => word[0]).join('').toUpperCase(), [user])
  const role = user?.roles[0]?.display_name ?? 'Utilizador'
  const visibleNavItems = useMemo(() => navigation.flatMap(group => group.items.filter(canAccessItem)), [navigation, canAccessItem])
  const searchResults = useMemo(() => {
    const value = searchTerm.trim().toLocaleLowerCase('pt-AO')
    if (!value) return visibleNavItems.slice(0, 8)
    return visibleNavItems.filter(item => item.label.toLocaleLowerCase('pt-AO').includes(value) || item.id.includes(value)).slice(0, 8)
  }, [searchTerm, visibleNavItems])
  const unreadNotifications = notifications.filter(item => item.status !== 'read').length

  function openModule(item: NavItem) {
    if (['dashboard', 'hr', 'employees', 'daily-reports', 'performance', 'departments', 'clients', 'equipment', 'inspections', 'certificates', 'fleet', 'trips', 'assets', 'finance', 'documents', 'audit', 'reports', 'sync', 'settings', 'ops', 'cloud-security', 'fleet-command', 'ai-automation', 'employee-portal', 'executive-saas', 'portal-requests', 'portal-billing'].includes(item.id)) {
      onNavigate(item.id as AppView); setMobileOpen(false); return
    }
    if (item.id === 'users-rbac' && user?.permissions.some(permission => permission === '*' || permission === 'users.manage')) {
      setUserAdminOpen(true); setMobileOpen(false); return
    }
    const phaseText = item.phase === 1 ? 'A gestão visual de RBAC será concluída nesta fase.' : `Módulo planeado para a Fase ${item.phase}.`
    setNotice(`${item.label}: ${phaseText}`)
    setMobileOpen(false)
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const target = searchResults[0]
    if (!target) {
      setNotice('Nenhum módulo encontrado para a pesquisa.')
      return
    }
    openModule(target)
    setSearchOpen(false)
    setSearchTerm('')
  }

  const loadNotifications = useCallback(async (open = true) => {
    setNotificationsBusy(true)
    try {
      const rows = await api.enterpriseNotifications()
      setNotifications(rows)
      if (open) setNotificationsOpen(true)
    } catch (err) {
      setNotice(err instanceof ApiError ? err.message : 'Não foi possível carregar notificações.')
    } finally {
      setNotificationsBusy(false)
    }
  }, [])

  async function markNotificationRead(notification: EnterpriseNotification) {
    try {
      const updated = await api.markNotificationRead(notification.id)
      setNotifications(current => current.map(item => item.id === updated.id ? updated : item))
    } catch (err) {
      setNotice(err instanceof ApiError ? err.message : 'Não foi possível atualizar a notificação.')
    }
  }

  function openSupport() {
    const subject = encodeURIComponent('Suporte FNLIFTING Enterprise ERP')
    const body = encodeURIComponent(`Utilizador: ${user?.full_name ?? 'n/d'}\nEmpresa: ${user?.company.name ?? 'n/d'}\n\nDescreva o problema:`)
    window.location.href = `mailto:suporte@fnlifting.com?subject=${subject}&body=${body}`
  }

  useEffect(() => {
    if (!user) return
    void loadNotifications(false)
  }, [user, loadNotifications])

  useEffect(() => {
    function handler(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        searchInput.current?.focus()
        setSearchOpen(true)
      }
      if (event.key === 'Escape') {
        setSearchOpen(false)
        setNotificationsOpen(false)
        setProfileOpen(false)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  return (
    <div className="erp-shell">
      {mobileOpen && <button className="sidebar-backdrop" onClick={() => setMobileOpen(false)} aria-label="Fechar menu" />}
      <aside className={cn('erp-sidebar', collapsed && 'collapsed', mobileOpen && 'mobile-open')}>
        <div className="sidebar-head">
          <BrandLogo compact className={cn(collapsed && 'justify-center [&>div:last-child]:hidden')} />
          <button className="collapse-button" onClick={() => setCollapsed(value => !value)}>{collapsed ? <PanelLeftOpen /> : <PanelLeftClose />}</button>
          <button className="mobile-close" onClick={() => setMobileOpen(false)}><X /></button>
        </div>
        <nav className="sidebar-nav">
          {navigation.map(group => {
            const visibleItems = group.items.filter(canAccessItem)
            if (!visibleItems.length) return null
            return <div className="nav-group" key={group.label}>
              <p>{group.label}</p>
              {visibleItems.map(item => {
                const NavIcon = item.icon
                return (
                  <button key={item.id} className={cn('nav-item', item.id === activeView && 'active')} onClick={() => openModule(item)} title={collapsed ? item.label : undefined}>
                    <NavIcon size={18} /><span>{item.label}</span>
                    {item.phase && item.phase > 1 && <small>F{item.phase}</small>}
                  </button>
                )
              })}
            </div>
          })}
        </nav>
        <div className="sidebar-footer">
          <div className="connection-status"><span /><div><strong>Modo local ativo</strong><small>SQLite · dados protegidos</small></div></div>
          <button className="sidebar-help" onClick={openSupport}><Headphones size={17} /><span>Central de suporte</span></button>
        </div>
      </aside>

      <div className={cn('erp-workspace', collapsed && 'sidebar-collapsed')}>
        <header className="erp-topbar">
          <button className="mobile-menu" onClick={() => setMobileOpen(true)}><Menu /></button>
          <form className="global-search" onSubmit={submitSearch}>
            <Search size={17} /><input ref={searchInput} value={searchTerm} onChange={event => { setSearchTerm(event.target.value); setSearchOpen(true) }} onFocus={() => setSearchOpen(true)} placeholder="Pesquisar no sistema..." /><kbd>Ctrl K</kbd>
            {searchOpen && <div className="global-search-results">
              {searchResults.map(item => {
                const ResultIcon = item.icon
                return <button key={item.id} type="button" onMouseDown={event => event.preventDefault()} onClick={() => { openModule(item); setSearchOpen(false); setSearchTerm('') }}><ResultIcon size={15} /><span>{item.label}</span>{item.phase && <small>F{item.phase}</small>}</button>
              })}
              {!searchResults.length && <p>Nenhum módulo encontrado.</p>}
            </div>}
          </form>
          <div className="topbar-actions">
            <div className="live-state"><span /> Sistema operacional</div>
            <button className="icon-button" aria-label="Notificações" onClick={() => notificationsOpen ? setNotificationsOpen(false) : void loadNotifications(true)} disabled={notificationsBusy}><Bell size={19} />{unreadNotifications > 0 && <i>{unreadNotifications}</i>}</button>
            <div className="topbar-divider" />
            <button className="user-menu" onClick={() => setProfileOpen(value => !value)}>
              <span className="avatar">{initials}</span>
              <span className="user-copy"><strong>{user?.full_name}</strong><small>{role}</small></span>
              <ChevronDown size={15} />
            </button>
            <button className="logout-shortcut" onClick={logout} title="Terminar sessão">Sair</button>
          </div>
        </header>
        <main className="erp-content">{children}</main>
      </div>
      {notice && <div className="phase-toast"><span><ShieldCheck size={17} /></span><p>{notice}</p><button onClick={() => setNotice(null)}><X size={15} /></button></div>}
      {notificationsOpen && <section className="topbar-popover notifications-popover"><header><strong>Notificações</strong><button onClick={() => setNotificationsOpen(false)}><X size={15} /></button></header>{notifications.map(item => <article key={item.id} className={item.status === 'read' ? 'read' : ''}><span>{item.level}</span><div><strong>{item.title}</strong><p>{item.message}</p><small>{new Date(item.created_at).toLocaleString('pt-AO')}</small></div>{item.status !== 'read' && <button onClick={() => void markNotificationRead(item)}>Lida</button>}</article>)}{!notifications.length && <p className="empty-popover">Sem notificações.</p>}</section>}
      {profileOpen && <section className="topbar-popover profile-popover"><header><strong>Conta</strong><button onClick={() => setProfileOpen(false)}><X size={15} /></button></header><div><span className="avatar">{initials}</span><p><strong>{user?.full_name}</strong><small>{user?.email}</small><small>{user?.company.name} · {role}</small></p></div><button onClick={() => { setProfileOpen(false); void logout() }}>Terminar sessão</button></section>}
      {userAdminOpen && <UserManagementDrawer onClose={() => setUserAdminOpen(false)} />}
    </div>
  )
}
