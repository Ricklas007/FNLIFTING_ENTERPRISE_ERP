import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  Activity, BadgeCheck, Bell, Boxes, Building2, ChevronDown, CircleDollarSign,
  ClipboardCheck, Command, FileBarChart, FileClock, FileText, Gauge, Headphones,
  LayoutDashboard, Menu, PackageCheck, PanelLeftClose, PanelLeftOpen, Search,
  Settings, ShieldCheck, Truck, UserCog, Users, WalletCards, X, Network,
} from 'lucide-react'
import { BrandLogo } from '@/components/BrandLogo'
import { UserManagementDrawer } from '@/components/UserManagementDrawer'
import { useAuth } from '@/store/AuthContext'
import { cn } from '@/lib/utils'
import type { AppView } from '@/types'

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
    { id: 'employee-portal', label: 'RH Enterprise', icon: Users, phase: 11, permission: 'hr.view' },
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
  const navigation = user?.account_type === 'external' ? clientNav : enterpriseNav

  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(null), 3400)
    return () => window.clearTimeout(timer)
  }, [notice])

  const initials = useMemo(() => user?.full_name.split(' ').slice(0, 2).map(word => word[0]).join('').toUpperCase(), [user])
  const role = user?.roles[0]?.display_name ?? 'Utilizador'

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
            const visibleItems = group.items.filter(item => !item.permission || user?.permissions.includes('*') || user?.permissions.includes(item.permission))
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
          <button className="sidebar-help"><Headphones size={17} /><span>Central de suporte</span></button>
        </div>
      </aside>

      <div className={cn('erp-workspace', collapsed && 'sidebar-collapsed')}>
        <header className="erp-topbar">
          <button className="mobile-menu" onClick={() => setMobileOpen(true)}><Menu /></button>
          <div className="global-search"><Search size={17} /><input placeholder="Pesquisar no sistema..." /><kbd>⌘ K</kbd></div>
          <div className="topbar-actions">
            <div className="live-state"><span /> Sistema operacional</div>
            <button className="icon-button" aria-label="Notificações"><Bell size={19} /><i>3</i></button>
            <div className="topbar-divider" />
            <button className="user-menu" onClick={() => setNotice('Menu do utilizador: utilize “Terminar sessão” para sair em segurança.')}>
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
      {userAdminOpen && <UserManagementDrawer onClose={() => setUserAdminOpen(false)} />}
    </div>
  )
}
