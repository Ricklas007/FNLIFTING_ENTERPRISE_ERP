export interface Role {
  name: string
  display_name: string
}

export interface Company {
  id: string
  name: string
  company_type: string
}

export interface User {
  id: string
  email: string
  username: string
  full_name: string
  account_type: 'internal' | 'external'
  status: string
  company: Company
  roles: Role[]
  permissions: string[]
  last_login_at?: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface MFARequiredResponse {
  mfa_required: true
  challenge_id: string
  expires_in: number
  user_hint: string
  delivery: 'totp'
}

export type LoginResponse = AuthResponse | MFARequiredResponse

export interface Metric {
  key: string
  label: string
  value: number
  display_value: string
  change: string
  trend: 'up' | 'down' | 'warning' | 'neutral'
  icon: string
}

export interface ChartPoint {
  label: string
  revenue: number
  expense: number
  inspections: number
}

export interface DashboardData {
  scope: 'enterprise' | 'client'
  greeting: string
  metrics: Metric[]
  finance_chart: ChartPoint[]
  operations_chart: ChartPoint[]
  alerts: { id: string; title: string; detail: string; level: string; time: string }[]
  activities: { id: string; title: string; detail: string; time: string; type: string }[]
  pending_approvals: number
}

export type AppView = 'dashboard' | 'hr' | 'employees' | 'daily-reports' | 'performance' | 'departments' | 'clients' | 'equipment' | 'inspections' | 'certificates' | 'fleet' | 'trips' | 'assets' | 'finance' | 'documents' | 'audit' | 'reports' | 'sync' | 'settings' | 'ops' | 'cloud-security' | 'fleet-command' | 'ai-automation' | 'employee-portal' | 'executive-saas' | 'portal-requests' | 'portal-billing'

export interface Department {
  id: string
  code: string
  name: string
  description?: string
  manager_name?: string
  status: 'active' | 'inactive'
  employee_count: number
  created_at: string
}

export interface Employee {
  id: string
  department_id: string
  user_id?: string
  employee_no: string
  full_name: string
  job_title: string
  birth_date?: string
  bi?: string
  nif?: string
  phone?: string
  email?: string
  address?: string
  admission_date: string
  contract_type: string
  salary?: string | number
  contract_status: string
  photo_url?: string
  status: 'active' | 'inactive' | 'on_leave'
  department: Department
  created_at: string
}

export interface DailyReport {
  id: string
  employee_id: string
  department_id: string
  report_date: string
  summary: string
  tasks_performed: string
  start_time?: string
  end_time?: string
  work_location?: string
  difficulties?: string
  results_achieved?: string
  observations?: string
  work_status: 'completed' | 'in_progress' | 'blocked'
  status: 'pending' | 'approved' | 'correction_requested'
  review_notes?: string
  reviewed_at?: string
  employee: Employee
  department: Department
  created_at: string
}

export interface PerformanceReview {
  id: string
  employee_id: string
  period: string
  punctuality: string | number
  productivity: string | number
  work_quality: string | number
  task_completion: string | number
  reports_score: string | number
  supervisor_score: string | number
  overall_score: string | number
  supervisor_notes?: string
  status: string
  employee: Employee
  created_at: string
}

export interface HRSummary {
  active_employees: number
  departments: number
  pending_reports: number
  reports_this_month: number
  average_performance: number
  employees_on_leave: number
  department_distribution: { name: string; value: number }[]
  top_performers: { name: string; job_title: string; score: number }[]
}

export interface Client {
  id: string
  name: string
  nif: string
  email?: string
  phone?: string
  address?: string
  contact_person?: string
  service_notes?: string
  status: 'active' | 'inactive' | 'prospect'
  equipment_count: number
  certificate_count: number
  created_at: string
}

export interface EquipmentType {
  id: string
  code: string
  name: string
  inspection_interval_months: number
  checklist_template?: string
  status: string
}

export interface Equipment {
  id: string
  client_id: string
  equipment_type_id: string
  code: string
  name: string
  manufacturer?: string
  model?: string
  serial_number?: string
  capacity?: string
  manufacture_year?: number
  location?: string
  status: 'approved' | 'rejected' | 'with_defect' | 'pending' | 'out_of_service'
  client: Client
  type: EquipmentType
  created_at: string
}

export interface ChecklistItem {
  id: string
  item_code: string
  item_label: string
  expected_result?: string
  result: 'pass' | 'fail' | 'na'
  notes?: string
}

export interface Inspection {
  id: string
  client_id: string
  equipment_id: string
  inspector_id?: string
  inspection_no: string
  inspection_date: string
  next_inspection_date?: string
  location?: string
  defects?: string
  recommendations?: string
  conclusion?: string
  status: 'approved' | 'rejected' | 'with_defect' | 'pending' | 'out_of_service'
  client: Client
  equipment: Equipment
  inspector?: { id: string; full_name: string; employee_no: string; job_title: string }
  checklist_items: ChecklistItem[]
  created_at: string
}

export interface Certificate {
  id: string
  client_id: string
  equipment_id: string
  inspection_id: string
  certificate_no: string
  document_type: string
  issued_at: string
  expires_at: string
  revision: number
  qr_token: string
  approver_signatory_id?: string
  service_order_no?: string
  report_no?: string
  identification_no?: string
  standard_reference: string
  colour_code?: string
  reason_code: string
  safe_to_use: boolean
  status: 'draft' | 'issued' | 'rejected'
  pdf_available: boolean
  client: Client
  equipment: Equipment
  inspection: Inspection
  approver_signatory?: TechnicalSignatory
  created_at: string
}

export interface TechnicalSignatory {
  id: string
  employee_id: string
  inspector_code: string
  qualifications: string
  employer_name: string
  employer_address?: string
  can_inspect: boolean
  can_approve: boolean
  status: 'active' | 'inactive'
  signature_available: boolean
  stamp_available: boolean
  employee: { id: string; full_name: string; employee_no: string; job_title: string }
  created_at: string
}

export interface OperationsSummary {
  active_clients: number
  equipment_total: number
  inspections_pending: number
  inspections_approved: number
  certificates_issued: number
  certificates_expiring: number
  equipment_by_status: { name: string; value: number }[]
}

export interface Driver {
  id: string
  employee_id?: string
  driver_code: string
  full_name: string
  license_number: string
  license_category: string
  license_expires_at: string
  phone?: string
  rating: number
  status: 'available' | 'on_trip' | 'inactive' | 'suspended'
  created_at: string
}

export interface TruckRecord {
  id: string
  driver_id?: string
  plate: string
  brand: string
  model: string
  manufacture_year?: number
  truck_type: string
  tank_capacity_liters?: number
  chassis_number?: string
  insurance_expires_at?: string
  license_expires_at?: string
  inspection_expires_at?: string
  status: 'available' | 'in_route' | 'maintenance' | 'out_of_service'
  driver?: Driver
  created_at: string
}

export interface TripRecord {
  id: string
  truck_id: string
  driver_id: string
  client_id?: string
  trip_code: string
  origin: string
  destination: string
  province: string
  city?: string
  fuel_type?: string
  quantity_liters?: number
  departure_at?: string
  expected_arrival_at?: string
  actual_arrival_at?: string
  notes?: string
  status: 'planned' | 'in_progress' | 'delivered' | 'delayed' | 'cancelled' | 'incident'
  truck: TruckRecord
  driver: Driver
  client?: Client
  created_at: string
}

export interface GPSPosition {
  id: string
  truck_id: string
  trip_id?: string
  latitude: number
  longitude: number
  speed_kmh: number
  heading?: number
  vehicle_state: 'moving' | 'stopped' | 'offline' | 'incident'
  fuel_level_percent?: number
  recorded_at: string
  truck: TruckRecord
}

export interface FleetSummary {
  drivers_total: number
  drivers_available: number
  trucks_total: number
  trucks_in_route: number
  trips_active: number
  trips_delayed: number
  open_incidents: number
  gps_online: number
}

export interface FleetIncident {
  id: string
  trip_id: string
  driver_id: string
  incident_type: string
  occurred_at: string
  location?: string
  description: string
  status: string
}

export interface GeofenceRecord {
  id: string
  name: string
  geofence_type: string
  shape_type: 'circle' | 'polygon' | 'corridor' | 'point'
  geometry: Record<string, unknown>
  radius_meters?: number
  alert_on_enter: boolean
  alert_on_exit: boolean
  dwell_minutes?: number
  status: string
  created_at: string
}

export interface FleetAlertRecord {
  id: string
  truck_id?: string
  trip_id?: string
  alert_type: string
  severity: 'info' | 'warning' | 'critical'
  title: string
  message: string
  status: string
  triggered_at: string
  resolved_at?: string
  payload: Record<string, unknown>
}

export interface GPSProviderRecord {
  code: string
  name: string
  provider_type: string
  status: 'CONNECTED' | 'CONFIGURED_NOT_TESTED' | 'DISCONNECTED' | 'AUTH_ERROR' | 'PROTOCOL_UNSUPPORTED' | string
  requires_credentials: boolean
  configured: boolean
  capabilities: string[]
  notes?: string
}

export interface GPSProviderHealth {
  code: string
  status: string
  message: string
  configured: boolean
  tested_at: string
}

export interface GPSTrackerDeviceRecord {
  id: string
  device_uid: string
  label: string
  truck_id?: string
  driver_id?: string
  provider: string
  capabilities: string[]
  status: string
  last_seen_at?: string
  created_at: string
}

export interface TraccarStatus {
  provider: 'TRACCAR'
  status: string
  configured: boolean
  base_url?: string
  message: string
  checked_at: string
}

export interface TraccarDevice {
  external_id: string
  name: string
  unique_id?: string
  status?: string
  phone?: string
  model?: string
  category?: string
  last_update?: string
}

export interface MapPlaceResult {
  external_id: string
  title: string
  category?: string
  address?: string
  phone?: string
  website?: string
  latitude: number
  longitude: number
  rating?: number
  reviews?: number
  hours?: string
  thumbnail?: string
  source: string
  retrieved_at: string
}

export interface GPSReplayData {
  mode: string
  count: number
  bounds?: [number, number, number, number]
  positions: {
    id: string
    truck_id: string
    trip_id?: string
    latitude: number
    longitude: number
    speed_kmh: number
    heading?: number
    vehicle_state: string
    fuel_level_percent?: number
    recorded_at: string
  }[]
  stops: Record<string, unknown>[]
}

export interface AssetRecord {
  id: string
  asset_code: string
  name: string
  category: string
  description?: string
  brand?: string
  model?: string
  serial_number?: string
  acquisition_date?: string
  acquisition_value: number | string
  current_value?: number | string
  depreciation_rate: number | string
  location?: string
  responsible_id?: string
  notes?: string
  status: 'active' | 'maintenance' | 'transferred' | 'retired' | 'lost'
  responsible?: { id: string; full_name: string; employee_no: string; job_title: string }
  maintenance_count: number
  transfer_count: number
  created_at: string
}

export interface AssetSummary {
  total_assets: number
  active_assets: number
  in_maintenance: number
  maintenance_due: number
  acquisition_value: number | string
  current_value: number | string
  by_category: { name: string; value: number }[]
}

export interface ExpenseRecord {
  id: string
  department_id?: string
  responsible_id?: string
  category: string
  amount: number | string
  transaction_date: string
  description: string
  vendor?: string
  due_date?: string
  payment_method?: string
  status: 'pending' | 'approved' | 'paid' | 'rejected'
  department_name?: string
  responsible_name?: string
  approved_at?: string
  created_at: string
}

export interface RevenueRecord {
  id: string
  client_id: string
  invoice_id?: string
  amount: number | string
  transaction_date: string
  description: string
  service?: string
  payment_method?: string
  reference?: string
  status: 'pending' | 'paid' | 'cancelled'
  client: Client
  paid_at?: string
  created_at: string
}

export interface InvoiceItem {
  id: string
  description: string
  quantity: number | string
  unit_price: number | string
  tax_rate: number | string
  line_total: number | string
}

export interface InvoiceRecord {
  id: string
  client_id: string
  invoice_no: string
  issue_date: string
  due_date: string
  currency: string
  subtotal: number | string
  tax_amount: number | string
  total_amount: number | string
  paid_amount: number | string
  balance_due: number | string
  notes?: string
  status: 'draft' | 'issued' | 'partial' | 'paid' | 'overdue' | 'cancelled'
  pdf_available: boolean
  client: Client
  items: InvoiceItem[]
  created_at: string
}

export interface ReceiptRecord {
  id: string
  client_id: string
  invoice_id: string
  payment_id: string
  receipt_no: string
  issued_at: string
  amount: number | string
  status: string
  pdf_available: boolean
  client: Client
  invoice: InvoiceRecord
  created_at: string
}

export interface FinanceSummary {
  revenue_total: number | string
  expense_total: number | string
  profit: number | string
  receivables: number | string
  payables: number | string
  invoices_open: number
  expenses_pending: number
  cash_flow: { period: string; revenue: number; expense: number }[]
  expenses_by_category: { name: string; value: number }[]
}

export interface DocumentVersion {
  id: string
  version_no: number
  file_name: string
  mime_type: string
  file_size: number
  checksum_sha256: string
  change_notes?: string
  created_at: string
}

export interface DocumentRecord {
  id: string
  client_id?: string
  employee_id?: string
  document_no: string
  title: string
  category: string
  description?: string
  current_version: number
  valid_until?: string
  approval_status: 'pending' | 'approved' | 'rejected'
  status: string
  client?: Client
  employee?: { id: string; full_name: string; employee_no: string; job_title: string }
  versions: DocumentVersion[]
  created_at: string
}

export interface AuditLogRecord {
  id: string
  user_id?: string
  user_name?: string
  action: string
  entity_type: string
  entity_id?: string
  entity_label?: string
  before_data?: string
  after_data?: string
  ip_address?: string
  machine_name?: string
  description?: string
  created_at: string
}

export interface AuditSummary {
  total_events: number
  events_today: number
  active_users: number
  sensitive_actions: number
  by_action: { name: string; value: number }[]
}

export interface SyncSummary {
  connection: 'local' | 'ready'
  mode: 'local_checkpoint' | 'remote'
  remote_configured: boolean
  pending: number
  synced: number
  conflicts: number
  failed: number
  last_sync_at?: string
  last_sync_status?: string
  database: string
}

export interface SyncQueueRecord {
  id: string
  entity_type: string
  entity_id: string
  operation: 'create' | 'update' | 'delete'
  payload: string
  base_version?: string
  status: 'pending' | 'synced' | 'conflict' | 'failed'
  retry_count: number
  error_message?: string
  conflict_payload?: string
  queued_at: string
  processed_at?: string
}

export interface SyncRunRecord {
  id: string
  direction: string
  mode: string
  started_at: string
  completed_at?: string
  pushed_count: number
  pulled_count: number
  conflict_count: number
  failed_count: number
  status: string
  message?: string
}

export interface BackupRecord {
  id: string
  backup_no: string
  file_name: string
  file_size: number
  checksum_sha256: string
  format_version: string
  encrypted: boolean
  includes_files: boolean
  status: string
  triggered_by: string
  restored_at?: string
  notes?: string
  created_at: string
}

export interface SystemSetting {
  id: string
  key: string
  label: string
  value: string
  value_type: 'string' | 'boolean' | 'integer'
  category: string
  is_secret: boolean
  description?: string
  updated_at: string
}

export interface ServiceRequestRecord {
  id: string
  request_no: string
  service_type: string
  requested_date: string
  preferred_date?: string
  location: string
  contact_name: string
  contact_phone?: string
  priority: 'low' | 'normal' | 'high' | 'urgent'
  notes?: string
  status: 'submitted' | 'reviewing' | 'scheduled' | 'completed' | 'rejected' | 'cancelled'
  response_notes?: string
  handled_at?: string
  client: Client
  equipment?: Equipment
  created_at: string
}

export interface PortalOverview {
  client_name: string
  equipment_total: number
  certificates_valid: number
  certificates_expiring: number
  invoices_open: number
  amount_due: number
  documents_available: number
  requests_open: number
  latest_requests: ServiceRequestRecord[]
}

export interface PortalBilling {
  invoices: InvoiceRecord[]
  receipts: ReceiptRecord[]
}

export interface ReportMetric {
  key: string
  label: string
  value: number
  display_value: string
  variation?: number
}

export interface AdvancedReport {
  report_type: string
  title: string
  date_from: string
  date_to: string
  generated_at: string
  metrics: ReportMetric[]
  series: { period: string; revenue: number; expense: number; inspections: number; trips: number }[]
  breakdowns: Record<string, { name: string; value: number }[]>
  highlights: string[]
}

export interface ReadinessCheck {
  key: string
  label: string
  status: 'pass' | 'warn' | 'fail'
  message: string
  recommendation?: string
}

export interface ReadinessReport {
  status: 'ready' | 'not_ready'
  environment: string
  version: string
  generated_at: string
  database: string
  auto_create_schema: boolean
  summary: { pass: number; warn: number; fail: number }
  checks: ReadinessCheck[]
  deployment: {
    docker_ready: boolean
    migrations_ready: boolean
    frontend_runtime: string
  }
}

export interface EnterpriseOverview {
  version: string
  provider_mode: string
  remote_configured: boolean
  phases: { phase: number; title: string; status: string }[]
  metrics: Record<string, number>
  security: { mfa_enabled: boolean }
}

export interface EnterpriseNotification {
  id: string
  title: string
  message: string
  level: string
  status: string
  created_at: string
}

export interface EnterpriseDevice {
  id: string
  device_uid: string
  name: string
  platform: string
  app_version?: string
  capabilities: string[]
  trust_level: string
  status: string
  last_seen_at: string
}

export interface SessionRecord {
  id: string
  user_agent?: string
  ip_address?: string
  expires_at: string
  revoked_at?: string
  created_at: string
  status: string
}

export interface MfaSetup {
  secret: string
  otpauth_uri: string
  qr_code_data_uri: string
  digits: number
  period: number
}

export interface FleetCommandCenter {
  summary: Record<string, number>
  trucks: { id: string; plate: string; status: string; driver_id?: string }[]
  commands: { id: string; command_type: string; priority: string; status: string; payload: Record<string, unknown>; truck_id?: string; trip_id?: string; due_at?: string; created_at: string }[]
  gps_events: { id: string; provider: string; latitude?: number; longitude?: number; payload: Record<string, unknown>; status: string; created_at: string }[]
}

export interface FleetComplianceCenter {
  summary: Record<string, number>
  items: {
    truck_id: string
    plate: string
    truck_type: string
    is_tanker: boolean
    is_trailer: boolean
    tank_capacity_liters?: number
    driver?: { id: string; name: string; license_category: string }
    documents: { type: string; label: string; status: string; valid_until?: string; days_remaining?: number }[]
    active_trip?: { id: string; trip_code: string; origin: string; destination: string; status: string }
    open_incidents: number
    fuel_liters_recorded: number
    latest_gps?: { latitude: number; longitude: number; speed_kmh: number; recorded_at: string }
    maintenance: { status: string; next_due?: string }
  }[]
}

export interface AutomationCenter {
  rules: { id: string; code: string; name: string; module: string; trigger_event: string; condition: Record<string, unknown>; action: Record<string, unknown>; severity: string; status: string }[]
  ocr_jobs: { id: string; source_filename: string; provider: string; status: string; confidence?: number; created_at: string }[]
  runs: { id: string; rule_id: string; entity_type?: string; entity_id?: string; result: string; detail: Record<string, unknown>; executed_at: string }[]
}

export interface AIAssistantCenter {
  summary: Record<string, number>
  suggestions: {
    id: string
    module: string
    source_type: string
    source_id?: string
    title: string
    recommendation: string
    rationale?: string
    action: Record<string, unknown>
    status: string
    reviewed_at?: string
    applied_at?: string
    created_at: string
  }[]
}

export interface EmployeePortal {
  employee?: { id: string; full_name: string; job_title: string }
  attendance: { id: string; employee_id: string; work_date: string; status: string; approval_status: string; location?: string }[]
  leave_requests: { id: string; employee_id: string; leave_type: string; start_date: string; end_date: string; status: string }[]
  payroll_runs: { id: string; period: string; status: string; gross_total: number; net_total: number }[]
}

export interface OrgChart {
  summary: Record<string, number>
  positions: {
    id: string
    code: string
    title: string
    level: number
    status: string
    department?: { id: string; name: string; code: string }
    employee?: { id: string; full_name: string; job_title: string }
    supervisor_position_id?: string
    children?: OrgChart['positions']
  }[]
  tree: OrgChart['positions']
}

export interface ExecutiveBI {
  scorecards: { key: string; label: string; value: number; display: string }[]
  risk: { level: string; remote_sync: boolean; provider: string }
}

export interface ComplianceItem {
  id: string
  code: string
  title: string
  category: string
  authority?: string
  due_date?: string
  risk_level: string
  status: string
}

export interface LicenseStatus {
  company?: { id: string; name: string; type: string }
  license?: { id: string; plan_code: string; seats: number; modules: string[]; starts_at: string; expires_at?: string; status: string; usage: Record<string, unknown> }
}
