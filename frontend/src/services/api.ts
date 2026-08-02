import type {
  AuthResponse, DailyReport, DashboardData, Department, Employee, HRSummary,
  PerformanceReview, User, Client, Equipment, EquipmentType, Inspection,
  Certificate, OperationsSummary, TechnicalSignatory, Driver, TruckRecord,
  TripRecord, GPSPosition, FleetSummary, FleetIncident, AssetRecord, AssetSummary,
  ExpenseRecord, RevenueRecord, InvoiceRecord, ReceiptRecord, FinanceSummary,
  DocumentRecord, AuditLogRecord, AuditSummary, AdvancedReport, BackupRecord,
  PortalBilling, PortalOverview, ReadinessReport, ServiceRequestRecord, SyncQueueRecord, SyncRunRecord,
  SyncSummary, SystemSetting, LoginResponse, MfaSetup, EnterpriseOverview, EnterpriseNotification,
  EnterpriseDevice, SessionRecord, FleetCommandCenter, FleetComplianceCenter, AutomationCenter, AIAssistantCenter, EmployeePortal, OrgChart, ExecutiveBI,
  ComplianceItem, LicenseStatus, GeofenceRecord, FleetAlertRecord, GPSProviderHealth, GPSProviderRecord, GPSReplayData, GPSTrackerDeviceRecord, MapPlaceResult, OperationalPlaceRecord,
  SerpApiStatus, TraccarDevice, TraccarStatus,
} from '@/types'

declare global {
  interface Window {
    fnliftingDesktop?: {
      getApiBaseUrl?: () => Promise<string>
    }
  }
}

const API_URL = import.meta.env.VITE_API_URL ?? '/api/v1'
let runtimeApiUrl: string | null = null

if (typeof window !== 'undefined' && window.fnliftingDesktop?.getApiBaseUrl) {
  void window.fnliftingDesktop.getApiBaseUrl().then((value) => {
    runtimeApiUrl = value || null
  }).catch(() => {
    runtimeApiUrl = null
  })
}

export function apiUrl(path: string): string {
  return `${runtimeApiUrl ?? API_URL}${path}`
}

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message)
  }
}

function getStorage(): Storage {
  return localStorage.getItem('fnl_remember') === 'true' ? localStorage : sessionStorage
}

export const tokenStore = {
  save(response: AuthResponse, remember: boolean) {
    localStorage.setItem('fnl_remember', String(remember))
    const storage = remember ? localStorage : sessionStorage
    const other = remember ? sessionStorage : localStorage
    storage.setItem('fnl_access_token', response.access_token)
    storage.setItem('fnl_refresh_token', response.refresh_token)
    other.removeItem('fnl_access_token')
    other.removeItem('fnl_refresh_token')
  },
  access: () => getStorage().getItem('fnl_access_token'),
  refresh: () => getStorage().getItem('fnl_refresh_token'),
  clear() {
    for (const storage of [localStorage, sessionStorage]) {
      storage.removeItem('fnl_access_token')
      storage.removeItem('fnl_refresh_token')
    }
    localStorage.removeItem('fnl_remember')
  },
}

async function request<T>(path: string, options: RequestInit = {}, authenticated = false): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  if (authenticated) {
    const token = tokenStore.access()
    if (token) headers.set('Authorization', `Bearer ${token}`)
  }
  let response: Response
  try {
    response = await fetch(apiUrl(path), { ...options, headers })
  } catch {
    throw new ApiError('Não foi possível ligar ao servidor local. Confirme que o backend está em execução.', 0)
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const detail = Array.isArray(payload?.detail)
      ? payload.detail.map((item: { msg: string }) => item.msg).join('. ')
      : typeof payload?.detail === 'object' && payload.detail !== null
        ? (payload.detail.message || JSON.stringify(payload.detail))
        : payload?.detail
    throw new ApiError(detail || 'Ocorreu um erro inesperado.', response.status)
  }
  return response.json() as Promise<T>
}

async function download(path: string, filename: string) {
  const headers = new Headers()
  const token = tokenStore.access()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(apiUrl(path), { headers })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(payload?.detail || 'Não foi possível descarregar o documento.', response.status)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url; anchor.download = filename; anchor.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

async function preview(path: string) {
  const headers = new Headers()
  const token = tokenStore.access()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(apiUrl(path), { headers })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(payload?.detail || 'Não foi possível pré-visualizar o documento.', response.status)
  }
  return URL.createObjectURL(await response.blob())
}

export const api = {
  login: (payload: { identifier: string; password: string; portal: 'staff' | 'client'; remember_me: boolean }) =>
    request<LoginResponse>('/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  verifyMfaLogin: (payload: { challenge_id: string; code: string; remember_me: boolean }) =>
    request<AuthResponse>('/auth/login/mfa', { method: 'POST', body: JSON.stringify(payload) }),
  register: (payload: Record<string, string | undefined>) =>
    request<{ message: string }>('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  forgotPassword: () => request<{ message: string }>('/auth/forgot-password', { method: 'POST' }),
  me: () => request<User>('/auth/me', {}, true),
  dashboard: () => request<DashboardData>('/dashboard/overview', {}, true),
  users: () => request<User[]>('/admin/users', {}, true),
  approveUser: (userId: string) => request<{ message: string }>(`/admin/users/${userId}/approve`, { method: 'POST' }, true),
  hrSummary: () => request<HRSummary>('/hr/summary', {}, true),
  departments: () => request<Department[]>('/hr/departments?include_inactive=true', {}, true),
  createDepartment: (payload: Record<string, unknown>) => request<Department>('/hr/departments', { method: 'POST', body: JSON.stringify(payload) }, true),
  updateDepartment: (id: string, payload: Record<string, unknown>) => request<Department>(`/hr/departments/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }, true),
  deleteDepartment: (id: string) => request<{ message: string }>(`/hr/departments/${id}`, { method: 'DELETE' }, true),
  employees: (params = '') => request<Employee[]>(`/hr/employees${params ? `?${params}` : ''}`, {}, true),
  myEmployee: () => request<Employee>('/hr/employees/me', {}, true),
  createEmployee: (payload: Record<string, unknown>) => request<Employee>('/hr/employees', { method: 'POST', body: JSON.stringify(payload) }, true),
  updateEmployee: (id: string, payload: Record<string, unknown>) => request<Employee>(`/hr/employees/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }, true),
  deleteEmployee: (id: string) => request<{ message: string }>(`/hr/employees/${id}`, { method: 'DELETE' }, true),
  dailyReports: (params = '') => request<DailyReport[]>(`/hr/daily-reports${params ? `?${params}` : ''}`, {}, true),
  createDailyReport: (payload: Record<string, unknown>) => request<DailyReport>('/hr/daily-reports', { method: 'POST', body: JSON.stringify(payload) }, true),
  updateDailyReport: (id: string, payload: Record<string, unknown>) => request<DailyReport>(`/hr/daily-reports/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }, true),
  reviewDailyReport: (id: string, action: 'approve' | 'request_correction', notes?: string) => request<DailyReport>(`/hr/daily-reports/${id}/review`, { method: 'POST', body: JSON.stringify({ action, notes }) }, true),
  performance: (params = '') => request<PerformanceReview[]>(`/hr/performance${params ? `?${params}` : ''}`, {}, true),
  createPerformance: (payload: Record<string, unknown>) => request<PerformanceReview>('/hr/performance', { method: 'POST', body: JSON.stringify(payload) }, true),
  operationsSummary: () => request<OperationsSummary>('/operations/summary', {}, true),
  clients: () => request<Client[]>('/operations/clients', {}, true),
  createClient: (payload: Record<string, unknown>) => request<Client>('/operations/clients', { method: 'POST', body: JSON.stringify(payload) }, true),
  updateClient: (id: string, payload: Record<string, unknown>) => request<Client>(`/operations/clients/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }, true),
  deleteClient: (id: string) => request<{ message: string }>(`/operations/clients/${id}`, { method: 'DELETE' }, true),
  equipmentTypes: () => request<EquipmentType[]>('/operations/equipment-types', {}, true),
  equipment: () => request<Equipment[]>('/operations/equipment', {}, true),
  createEquipment: (payload: Record<string, unknown>) => request<Equipment>('/operations/equipment', { method: 'POST', body: JSON.stringify(payload) }, true),
  updateEquipment: (id: string, payload: Record<string, unknown>) => request<Equipment>(`/operations/equipment/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }, true),
  deleteEquipment: (id: string) => request<{ message: string }>(`/operations/equipment/${id}`, { method: 'DELETE' }, true),
  inspections: () => request<Inspection[]>('/operations/inspections', {}, true),
  createInspection: (payload: Record<string, unknown>) => request<Inspection>('/operations/inspections', { method: 'POST', body: JSON.stringify(payload) }, true),
  updateInspection: (id: string, payload: Record<string, unknown>) => request<Inspection>(`/operations/inspections/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }, true),
  certificates: () => request<Certificate[]>('/operations/certificates', {}, true),
  signatories: (capability = '') => request<TechnicalSignatory[]>(`/operations/signatories${capability ? `?capability=${capability}` : ''}`, {}, true),
  createSignatory: (payload: Record<string, unknown>) => request<TechnicalSignatory>('/operations/signatories', { method: 'POST', body: JSON.stringify(payload) }, true),
  updateSignatory: (id: string, payload: Record<string, unknown>) => request<TechnicalSignatory>(`/operations/signatories/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }, true),
  createCertificate: (payload: Record<string, unknown> | string) => request<Certificate>('/operations/certificates', { method: 'POST', body: JSON.stringify(typeof payload === 'string' ? { inspection_id: payload } : payload) }, true),
  updateCertificate: (id: string, payload: Record<string, unknown>) => request<Certificate>(`/operations/certificates/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }, true),
  issueCertificate: (id: string) => request<Certificate>(`/operations/certificates/${id}/issue`, { method: 'POST' }, true),
  downloadCertificate: (id: string, number: string) => download(`/operations/certificates/${id}/pdf`, `${number}.pdf`),
  previewCertificate: (id: string) => preview(`/operations/certificates/${id}/pdf`),
  fleetSummary: () => request<FleetSummary>('/fleet/summary', {}, true),
  drivers: () => request<Driver[]>('/fleet/drivers', {}, true),
  createDriver: (payload: Record<string, unknown>) => request<Driver>('/fleet/drivers', { method: 'POST', body: JSON.stringify(payload) }, true),
  updateDriver: (id: string, payload: Record<string, unknown>) => request<Driver>(`/fleet/drivers/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }, true),
  deleteDriver: (id: string) => request<{ message: string }>(`/fleet/drivers/${id}`, { method: 'DELETE' }, true),
  trucks: () => request<TruckRecord[]>('/fleet/trucks', {}, true),
  createTruck: (payload: Record<string, unknown>) => request<TruckRecord>('/fleet/trucks', { method: 'POST', body: JSON.stringify(payload) }, true),
  updateTruck: (id: string, payload: Record<string, unknown>) => request<TruckRecord>(`/fleet/trucks/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }, true),
  deleteTruck: (id: string) => request<{ message: string }>(`/fleet/trucks/${id}`, { method: 'DELETE' }, true),
  trips: () => request<TripRecord[]>('/fleet/trips', {}, true),
  createTrip: (payload: Record<string, unknown>) => request<TripRecord>('/fleet/trips', { method: 'POST', body: JSON.stringify(payload) }, true),
  updateTrip: (id: string, payload: Record<string, unknown>) => request<TripRecord>(`/fleet/trips/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }, true),
  livePositions: () => request<GPSPosition[]>('/fleet/gps/live', {}, true),
  gpsReplay: (params: string) => request<GPSReplayData>(`/fleet/gps/replay?${params}`, {}, true),
  gpsGeojsonUrl: (params: string) => apiUrl(`/fleet/gps/export.geojson?${params}`),
  geofences: () => request<GeofenceRecord[]>('/fleet/geofences', {}, true),
  createGeofence: (payload: Record<string, unknown>) => request<GeofenceRecord>('/fleet/geofences', { method: 'POST', body: JSON.stringify(payload) }, true),
  operationalPlaces: (params = 'status=active') => request<OperationalPlaceRecord[]>(`/fleet/operational-places?${params}`, {}, true),
  createOperationalPlace: (payload: Record<string, unknown>) => request<OperationalPlaceRecord>('/fleet/operational-places', { method: 'POST', body: JSON.stringify(payload) }, true),
  fleetAlerts: (status = 'open') => request<FleetAlertRecord[]>(`/fleet/alerts?status=${encodeURIComponent(status)}`, {}, true),
  resolveFleetAlert: (id: string) => request<{ message: string }>(`/fleet/alerts/${id}/resolve`, { method: 'POST' }, true),
  gpsProviders: () => request<GPSProviderRecord[]>('/fleet/gps/providers', {}, true),
  gpsDevices: () => request<GPSTrackerDeviceRecord[]>('/fleet/gps/devices', {}, true),
  testGpsProvider: (code: string) => request<GPSProviderHealth>(`/fleet/gps/providers/${encodeURIComponent(code)}/health`, { method: 'POST' }, true),
  traccarStatus: () => request<TraccarStatus>('/integrations/traccar/status', {}, true),
  testTraccar: () => request<TraccarStatus>('/integrations/traccar/test', { method: 'POST' }, true),
  traccarDevices: () => request<TraccarDevice[]>('/integrations/traccar/devices', {}, true),
  importTraccarDevices: (deviceIds: string[]) => request<TraccarDevice[]>('/integrations/traccar/import-devices', { method: 'POST', body: JSON.stringify({ device_ids: deviceIds }) }, true),
  linkTraccarDevice: (deviceId: string, truckId: string) => request<TraccarDevice>('/integrations/traccar/link-device', { method: 'POST', body: JSON.stringify({ device_id: deviceId, truck_id: truckId }) }, true),
  testSerpApi: () => request<SerpApiStatus>('/integrations/serpapi/test', { method: 'POST' }, true),
  mapStatus: () => request<Record<string, unknown>>('/maps/status', {}, true),
  setMapMode: (mode: 'auto' | 'offline' | 'online') => request<Record<string, unknown>>('/maps/mode', { method: 'POST', body: JSON.stringify({ mode }) }, true),
  mapPackages: () => request<Record<string, unknown>[]>('/maps/packages', {}, true),
  activeMapPackage: () => request<Record<string, unknown>>('/maps/packages/active', {}, true),
  importMapPackage: (payload: Record<string, unknown>) => request<Record<string, unknown>>('/maps/packages/import', { method: 'POST', body: JSON.stringify(payload) }, true),
  validateMapPackage: (id: string) => request<Record<string, unknown>>(`/maps/packages/${id}/validate`, { method: 'POST' }, true),
  activateMapPackage: (id: string) => request<Record<string, unknown>>(`/maps/packages/${id}/activate`, { method: 'POST' }, true),
  deactivateMapPackage: () => request<Record<string, unknown>>('/maps/packages/deactivate', { method: 'POST' }, true),
  deactivateMapPackageById: (id: string) => request<Record<string, unknown>>(`/maps/packages/${id}/deactivate`, { method: 'POST' }, true),
  mapPackageMetadata: (id: string) => request<Record<string, unknown>>(`/maps/packages/${id}/metadata`, {}, true),
  removeMapPackage: (id: string) => request<Record<string, unknown>>(`/maps/packages/${id}`, { method: 'DELETE' }, true),
  searchMapPlaces: (params: URLSearchParams) => request<MapPlaceResult[]>(`/maps/places/search?${params.toString()}`, {}, true),
  createGPSPosition: (payload: Record<string, unknown>) => request<GPSPosition>('/fleet/gps/positions', { method: 'POST', body: JSON.stringify(payload) }, true),
  incidents: () => request<FleetIncident[]>('/fleet/incidents', {}, true),
  assetSummary: () => request<AssetSummary>('/management/assets/summary', {}, true),
  assets: () => request<AssetRecord[]>('/management/assets', {}, true),
  createAsset: (payload: Record<string, unknown>) => request<AssetRecord>('/management/assets', { method: 'POST', body: JSON.stringify(payload) }, true),
  updateAsset: (id: string, payload: Record<string, unknown>) => request<AssetRecord>(`/management/assets/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }, true),
  createAssetMaintenance: (id: string, payload: Record<string, unknown>) => request(`/management/assets/${id}/maintenance`, { method: 'POST', body: JSON.stringify(payload) }, true),
  transferAsset: (id: string, payload: Record<string, unknown>) => request(`/management/assets/${id}/transfers`, { method: 'POST', body: JSON.stringify(payload) }, true),
  financeSummary: () => request<FinanceSummary>('/management/finance/summary', {}, true),
  expenses: () => request<ExpenseRecord[]>('/management/finance/expenses', {}, true),
  createExpense: (payload: Record<string, unknown>) => request<ExpenseRecord>('/management/finance/expenses', { method: 'POST', body: JSON.stringify(payload) }, true),
  approveExpense: (id: string) => request<ExpenseRecord>(`/management/finance/expenses/${id}/approve`, { method: 'POST' }, true),
  revenues: () => request<RevenueRecord[]>('/management/finance/revenues', {}, true),
  createRevenue: (payload: Record<string, unknown>) => request<RevenueRecord>('/management/finance/revenues', { method: 'POST', body: JSON.stringify(payload) }, true),
  invoices: () => request<InvoiceRecord[]>('/management/finance/invoices', {}, true),
  createInvoice: (payload: Record<string, unknown>) => request<InvoiceRecord>('/management/finance/invoices', { method: 'POST', body: JSON.stringify(payload) }, true),
  registerPayment: (id: string, payload: Record<string, unknown>) => request<ReceiptRecord>(`/management/finance/invoices/${id}/payments`, { method: 'POST', body: JSON.stringify(payload) }, true),
  downloadInvoice: (id: string, number: string) => download(`/management/finance/invoices/${id}/pdf`, `${number}.pdf`),
  receipts: () => request<ReceiptRecord[]>('/management/finance/receipts', {}, true),
  downloadReceipt: (id: string, number: string) => download(`/management/finance/receipts/${id}/pdf`, `${number}.pdf`),
  documents: () => request<DocumentRecord[]>('/management/documents', {}, true),
  createDocument: (payload: Record<string, unknown>) => request<DocumentRecord>('/management/documents', { method: 'POST', body: JSON.stringify(payload) }, true),
  updateDocument: (id: string, payload: Record<string, unknown>) => request<DocumentRecord>(`/management/documents/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }, true),
  addDocumentVersion: (id: string, payload: Record<string, unknown>) => request<DocumentRecord>(`/management/documents/${id}/versions`, { method: 'POST', body: JSON.stringify(payload) }, true),
  approveDocument: (id: string) => request<DocumentRecord>(`/management/documents/${id}/approve`, { method: 'POST' }, true),
  reviewDocument: (id: string, action: 'approve' | 'reject', notes?: string) => request<DocumentRecord>(`/management/documents/${id}/review`, { method: 'POST', body: JSON.stringify({ action, notes }) }, true),
  downloadDocument: (id: string, filename: string) => download(`/management/documents/${id}/download`, filename),
  previewDocument: (id: string, version?: number) => preview(`/management/documents/${id}/download${version ? `?version=${version}` : ''}`),
  auditSummary: () => request<AuditSummary>('/management/audit/summary', {}, true),
  auditLogs: () => request<AuditLogRecord[]>('/management/audit/logs', {}, true),
  syncSummary: () => request<SyncSummary>('/system/sync/summary', {}, true),
  syncQueue: (status = '') => request<SyncQueueRecord[]>(`/system/sync/queue${status ? `?status=${status}` : ''}`, {}, true),
  syncRuns: () => request<SyncRunRecord[]>('/system/sync/runs', {}, true),
  runSync: () => request<SyncRunRecord>('/system/sync/run', { method: 'POST', body: JSON.stringify({ limit: 500 }) }, true),
  resolveSyncConflict: (id: string, strategy: 'local' | 'remote') => request<SyncQueueRecord>(`/system/sync/conflicts/${id}/resolve`, { method: 'POST', body: JSON.stringify({ strategy }) }, true),
  backups: () => request<BackupRecord[]>('/system/backups', {}, true),
  createBackup: (payload: { password: string; include_files: boolean; notes?: string }) => request<BackupRecord>('/system/backups', { method: 'POST', body: JSON.stringify(payload) }, true),
  verifyBackup: (id: string, password: string) => request<{ valid: boolean; manifest: Record<string, unknown> }>(`/system/backups/${id}/verify`, { method: 'POST', body: JSON.stringify({ password, confirm: false }) }, true),
  restoreBackup: (id: string, password: string) => request<{ message: string }>(`/system/backups/${id}/restore`, { method: 'POST', body: JSON.stringify({ password, confirm: true }) }, true),
  downloadBackup: (id: string, filename: string) => download(`/system/backups/${id}/download`, filename),
  settings: () => request<SystemSetting[]>('/system/settings', {}, true),
  updateSetting: (id: string, value: string) => request<SystemSetting>(`/system/settings/${id}`, { method: 'PATCH', body: JSON.stringify({ value }) }, true),
  readiness: () => request<ReadinessReport>('/system/ops/readiness', {}, true),
  advancedReport: (params: string) => request<AdvancedReport>(`/system/reports/advanced?${params}`, {}, true),
  downloadReport: (params: string, format: 'pdf' | 'xlsx' | 'csv') => download(`/system/reports/export?format=${format}&${params}`, `FNLIFTING-relatorio.${format}`),
  portalOverview: () => request<PortalOverview>('/portal/overview', {}, true),
  portalRequests: () => request<ServiceRequestRecord[]>('/portal/requests', {}, true),
  createPortalRequest: (payload: Record<string, unknown>) => request<ServiceRequestRecord>('/portal/requests', { method: 'POST', body: JSON.stringify(payload) }, true),
  portalBilling: () => request<PortalBilling>('/portal/billing', {}, true),
  downloadPortalInvoice: (id: string, number: string) => download(`/portal/invoices/${id}/pdf`, `${number}.pdf`),
  downloadPortalReceipt: (id: string, number: string) => download(`/portal/receipts/${id}/pdf`, `${number}.pdf`),
  enterpriseOverview: () => request<EnterpriseOverview>('/enterprise/overview', {}, true),
  registerDevice: (payload: { device_uid: string; name: string; platform: string; app_version?: string; capabilities: string[] }) => request<EnterpriseDevice>('/enterprise/devices/register', { method: 'POST', body: JSON.stringify(payload) }, true),
  enterpriseDevices: () => request<EnterpriseDevice[]>('/enterprise/devices', {}, true),
  sessions: () => request<SessionRecord[]>('/enterprise/sessions', {}, true),
  revokeSession: (id: string) => request<{ message: string }>(`/enterprise/sessions/${id}`, { method: 'DELETE' }, true),
  setupMfa: () => request<MfaSetup>('/enterprise/security/mfa/setup', { method: 'POST' }, true),
  confirmMfa: (code: string) => request<{ message: string; recovery_codes: string[] }>('/enterprise/security/mfa/confirm', { method: 'POST', body: JSON.stringify({ code }) }, true),
  disableMfa: () => request<{ message: string }>('/enterprise/security/mfa/disable', { method: 'POST' }, true),
  enterpriseNotifications: () => request<EnterpriseNotification[]>('/enterprise/notifications', {}, true),
  generateEnterpriseNotifications: () => request<{ message: string }>('/enterprise/notifications/generate-demo', { method: 'POST' }, true),
  markNotificationRead: (id: string) => request<EnterpriseNotification>(`/enterprise/notifications/${id}/read`, { method: 'POST' }, true),
  enterpriseSyncStatus: () => request<Record<string, unknown>>('/enterprise/sync/status', {}, true),
  enterpriseSyncPush: (payload: Record<string, unknown>) => request<Record<string, unknown>>('/enterprise/sync/push', { method: 'POST', body: JSON.stringify(payload) }, true),
  fleetCommandCenter: () => request<FleetCommandCenter>('/enterprise/fleet/command-center', {}, true),
  fleetCompliance: () => request<FleetComplianceCenter>('/enterprise/fleet/compliance', {}, true),
  createFleetCommand: (payload: Record<string, unknown>) => request<Record<string, unknown>>('/enterprise/fleet/commands', { method: 'POST', body: JSON.stringify(payload) }, true),
  ingestGps: (payload: Record<string, unknown>) => request<Record<string, unknown>>('/enterprise/gps/ingest', { method: 'POST', body: JSON.stringify(payload) }, true),
  aiProviders: () => request<{ id: string; provider_type: string; provider_name: string; mode: string; endpoint_url?: string; status: string }[]>('/enterprise/ai/providers', {}, true),
  automationCenter: () => request<AutomationCenter>('/enterprise/ai/automation', {}, true),
  aiAssistant: () => request<AIAssistantCenter>('/enterprise/ai/assistant', {}, true),
  generateAiAssistant: () => request<{ count: number; suggestions: AIAssistantCenter['suggestions'] }>('/enterprise/ai/assistant/generate', { method: 'POST' }, true),
  reviewAiSuggestion: (id: string, payload: Record<string, unknown>) => request<Record<string, unknown>>(`/enterprise/ai/assistant/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }, true),
  createOcrJob: (payload: Record<string, unknown>) => request<Record<string, unknown>>('/enterprise/ai/ocr/jobs', { method: 'POST', body: JSON.stringify(payload) }, true),
  employeePortal: () => request<EmployeePortal>('/enterprise/hr/employee-portal', {}, true),
  orgChart: () => request<OrgChart>('/enterprise/hr/org-chart', {}, true),
  createPayrollRun: (period: string) => request<Record<string, unknown>>('/enterprise/hr/payroll-runs', { method: 'POST', body: JSON.stringify({ period }) }, true),
  executiveBI: () => request<ExecutiveBI>('/enterprise/bi/executive', {}, true),
  compliance: () => request<ComplianceItem[]>('/enterprise/compliance', {}, true),
  createCompliance: (payload: Record<string, unknown>) => request<Record<string, unknown>>('/enterprise/compliance', { method: 'POST', body: JSON.stringify(payload) }, true),
  licenseStatus: () => request<LicenseStatus>('/enterprise/saas/license', {}, true),
  updateLicense: (payload: Record<string, unknown>) => request<Record<string, unknown>>('/enterprise/saas/license', { method: 'PATCH', body: JSON.stringify(payload) }, true),
  logout: () => request<{ message: string }>('/auth/logout', { method: 'POST' }, true),
}
