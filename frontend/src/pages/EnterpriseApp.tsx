import { useState } from 'react'
import { DashboardLayout } from '@/layouts/DashboardLayout'
import { DashboardPage } from '@/pages/DashboardPage'
import { DepartmentsPage, DailyReportsPage, EmployeesPage, HRPage, PerformancePage } from '@/pages/HRPages'
import { ClientsPage, EquipmentPage, InspectionsPage } from '@/pages/OperationsPages'
import { CertificatesPage } from '@/pages/CertificatePages'
import { FleetPage, TripsPage } from '@/pages/FleetPages'
import { AssetsPage, AuditPage, DocumentsPage, FinancePage } from '@/pages/ManagementPages'
import { AIAutomationPage, CloudSecurityPage, EmployeePortalPage, ExecutiveSaaSPage, FleetCommandPage } from '@/pages/EnterprisePhasePages'
import { OpsReadinessPage, PortalBillingPage, PortalRequestsPage, ReportsPage, SettingsPage, SyncPage } from '@/pages/SystemPages'
import type { AppView } from '@/types'

export function EnterpriseApp() {
  const [activeView, setActiveView] = useState<AppView>('dashboard')
  const pages = {
    dashboard: <DashboardPage />,
    hr: <HRPage onNavigate={setActiveView} />,
    employees: <EmployeesPage />,
    'daily-reports': <DailyReportsPage />,
    performance: <PerformancePage />,
    departments: <DepartmentsPage />,
    clients: <ClientsPage />,
    equipment: <EquipmentPage />,
    inspections: <InspectionsPage />,
    certificates: <CertificatesPage />,
    fleet: <FleetPage />,
    trips: <TripsPage />,
    assets: <AssetsPage />,
    finance: <FinancePage />,
    documents: <DocumentsPage />,
    audit: <AuditPage />,
    reports: <ReportsPage />,
    sync: <SyncPage />,
    settings: <SettingsPage />,
    ops: <OpsReadinessPage />,
    'cloud-security': <CloudSecurityPage />,
    'fleet-command': <FleetCommandPage />,
    'ai-automation': <AIAutomationPage />,
    'employee-portal': <EmployeePortalPage />,
    'executive-saas': <ExecutiveSaaSPage />,
    'portal-requests': <PortalRequestsPage />,
    'portal-billing': <PortalBillingPage />,
  } satisfies Record<AppView, React.ReactNode>

  return (
    <DashboardLayout activeView={activeView} onNavigate={setActiveView}>
      {pages[activeView]}
    </DashboardLayout>
  )
}
