import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import {
  AlertTriangle, ArrowRightLeft, BarChart3, CalendarDays, Check,
  CircleDollarSign, Cloud, CloudOff, Command, Database, Download, FileCheck2,
  FileSpreadsheet, FileText, HardDriveDownload, History, LockKeyhole, MapPinned, PackageCheck,
  Plus, ReceiptText, RefreshCw, Save, Search, Settings2, ShieldCheck, UploadCloud, X,
} from 'lucide-react'
import { api, ApiError } from '@/services/api'
import { useOnlineStatus } from '@/hooks/useOnlineStatus'
import type {
  AdvancedReport, BackupRecord, Equipment, PortalBilling, PortalOverview,
  ReadinessReport, SerpApiStatus, ServiceRequestRecord, SyncQueueRecord, SyncRunRecord, SyncSummary, SystemSetting,
} from '@/types'
import { cn } from '@/lib/utils'

const money = (value: number | string) => new Intl.NumberFormat('pt-AO', { style: 'currency', currency: 'AOA', maximumFractionDigits: 0 }).format(Number(value))
const shortDate = (value?: string) => value ? new Date(value.includes('T') ? value : `${value}T00:00:00`).toLocaleDateString('pt-AO') : '—'
const statusLabel: Record<string, string> = { pending: 'Pendente', synced: 'Sincronizado', conflict: 'Conflito', failed: 'Falhou', submitted: 'Submetido', reviewing: 'Em análise', scheduled: 'Agendado', completed: 'Concluído', rejected: 'Rejeitado', cancelled: 'Cancelado', issued: 'Emitida', partial: 'Parcial', paid: 'Paga', overdue: 'Vencida', ready: 'Pronto', not_ready: 'Não pronto', pass: 'OK', warn: 'Aviso', fail: 'Falha' }

type SystemMapProvider = {
  available?: boolean
  configured?: boolean
  status?: string
  reason?: string
  message?: string
  style?: string
  role?: string
  last_success_at?: string
  last_error?: string
  rate_limit_per_minute?: number
  cache_ttl_seconds?: number
  metrics?: Record<string, unknown>
}

type SystemMapStatus = {
  mode?: 'auto' | 'offline' | 'online'
  default_provider?: string
  active_provider?: string
  offline_active?: boolean
  providers?: Record<string, SystemMapProvider>
  active_package?: { original_name?: string; provider?: string; imported_at?: string } | null
  packages?: Array<{ id: string; original_name?: string; provider?: string }>
}

function Header({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <header className="module-page-header"><div><span>{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{action}</header>
}

function Status({ value }: { value: string }) {
  return <span className={cn('ops-status', value)}>{statusLabel[value] ?? value}</span>
}

function Feedback({ error }: { error: string | null }) {
  return error ? <div className="module-error"><AlertTriangle /><span>{error}</span></div> : null
}

function Dialog({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  return <div className="module-modal-layer"><button className="module-modal-backdrop" onClick={onClose} aria-label="Fechar diálogo" /><section className="module-modal"><header><div><span>FNLIFTING · Operação protegida</span><h2>{title}</h2></div><button onClick={onClose} aria-label="Fechar"><X /></button></header><div className="module-modal-body">{children}</div></section></div>
}

const sixMonthsAgo = () => {
  const now = new Date(); now.setMonth(now.getMonth() - 5); now.setDate(1)
  return now.toISOString().slice(0, 10)
}

export function ReportsPage() {
  const [report, setReport] = useState<AdvancedReport | null>(null)
  const [type, setType] = useState('executive')
  const [from, setFrom] = useState(sixMonthsAgo)
  const [to, setTo] = useState(new Date().toISOString().slice(0, 10))
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const params = useMemo(() => new URLSearchParams({ report_type: type, date_from: from, date_to: to }).toString(), [type, from, to])
  const load = useCallback(async () => { setLoading(true); setError(null); try { setReport(await api.advancedReport(params)) } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Não foi possível gerar o relatório.') } finally { setLoading(false) } }, [params])
  useEffect(() => { void load() }, [load])
  const maxFlow = Math.max(1, ...(report?.series.flatMap(item => [item.revenue, item.expense]) ?? [1]))

  return <>
    <Header eyebrow="Inteligência · Fase 6" title="Relatórios avançados" description="Análise executiva integrada de finanças, operações, pessoas, frota e património." action={<div className="report-export-actions"><button onClick={() => void api.downloadReport(params, 'pdf')}><FileText /> PDF</button><button onClick={() => void api.downloadReport(params, 'xlsx')}><FileSpreadsheet /> Excel</button><button onClick={() => void api.downloadReport(params, 'csv')}><Download /> CSV</button></div>} />
    <Feedback error={error} />
    <section className="report-filter-bar"><label>Relatório<select value={type} onChange={event => setType(event.target.value)}><option value="executive">Executivo consolidado</option><option value="financial">Financeiro</option><option value="operations">Operações técnicas</option><option value="hr">Pessoas e desempenho</option><option value="fleet">Frota e logística</option><option value="assets">Património</option></select></label><label>De<input type="date" value={from} onChange={event => setFrom(event.target.value)} /></label><label>Até<input type="date" value={to} onChange={event => setTo(event.target.value)} /></label><button onClick={() => void load()} disabled={loading}><RefreshCw className={loading ? 'spin' : ''} /> Atualizar</button></section>
    {loading || !report ? <div className="module-loading"><RefreshCw className="spin" /> A consolidar indicadores...</div> : <>
      <section className="report-metric-grid">{report.metrics.slice(0, 10).map((metric, index) => { const MetricIcon = [CircleDollarSign, BarChart3, FileCheck2, PackageCheck][index % 4]; return <article key={metric.key}><span><MetricIcon /></span><small>{metric.label}</small><strong>{metric.display_value}</strong></article> })}</section>
      <section className="report-dashboard-grid"><article className="report-flow-card"><header><BarChart3 /><div><h2>Evolução mensal</h2><p>Receita, despesa e volume operacional</p></div></header><div className="report-bars">{report.series.map(point => <div key={point.period}><div><i style={{ height: `${Math.max(5, point.revenue / maxFlow * 100)}%` }} /><i style={{ height: `${Math.max(5, point.expense / maxFlow * 100)}%` }} /></div><span>{point.period.slice(5)}</span></div>)}</div><footer><span><i /> Receita</span><span><i /> Despesa</span></footer></article><article className="report-highlights"><header><ShieldCheck /><div><h2>Destaques executivos</h2><p>Leitura automática do período</p></div></header>{report.highlights.map(item => <p key={item}><Check /> {item}</p>)}</article></section>
      <section className="report-breakdowns">{Object.entries(report.breakdowns).map(([name, rows]) => <article key={name}><header><h2>{name}</h2><span>{rows.length} grupos</span></header>{rows.slice(0, 6).map(row => { const max = Math.max(...rows.map(item => item.value), 1); return <div key={row.name}><p><span>{row.name}</span><strong>{row.value >= 10000 ? money(row.value) : row.value.toLocaleString('pt-AO')}</strong></p><i><b style={{ width: `${Math.max(3, row.value / max * 100)}%` }} /></i></div> })}</article>)}</section>
    </>}
  </>
}

export function SyncPage() {
  const online = useOnlineStatus()
  const [summary, setSummary] = useState<SyncSummary | null>(null)
  const [queue, setQueue] = useState<SyncQueueRecord[]>([])
  const [runs, setRuns] = useState<SyncRunRecord[]>([])
  const [backups, setBackups] = useState<BackupRecord[]>([])
  const [tab, setTab] = useState<'queue' | 'history' | 'backups'>('queue')
  const [busy, setBusy] = useState(false)
  const [dialog, setDialog] = useState<'create' | 'restore' | null>(null)
  const [selected, setSelected] = useState<BackupRecord | null>(null)
  const [error, setError] = useState<string | null>(null)
  const load = useCallback(async () => { setError(null); try { const [s, q, r, b] = await Promise.all([api.syncSummary(), api.syncQueue(), api.syncRuns(), api.backups()]); setSummary(s); setQueue(q); setRuns(r); setBackups(b) } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Não foi possível carregar o centro de sincronização.') } }, [])
  useEffect(() => { void load() }, [load])
  async function synchronize() { setBusy(true); setError(null); try { await api.runSync(); await load() } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'A sincronização não foi concluída.') } finally { setBusy(false) } }
  async function resolve(id: string, strategy: 'local' | 'remote') { setBusy(true); try { await api.resolveSyncConflict(id, strategy); await load() } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Não foi possível resolver o conflito.') } finally { setBusy(false) } }
  async function submitBackup(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setBusy(true); const data = new FormData(event.currentTarget); try { await api.createBackup({ password: String(data.get('password')), include_files: data.get('include_files') === 'on', notes: String(data.get('notes') || '') || undefined }); setDialog(null); await load() } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Não foi possível criar o backup.') } finally { setBusy(false) } }
  async function restore(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!selected) return; setBusy(true); const data = new FormData(event.currentTarget); try { await api.verifyBackup(selected.id, String(data.get('password'))); await api.restoreBackup(selected.id, String(data.get('password'))); setDialog(null); window.location.reload() } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Não foi possível restaurar o backup.') } finally { setBusy(false) } }

  return <>
    <Header eyebrow="Continuidade · Fase 6" title="Backup & Sync" description="Proteção cifrada, fila local, conflitos explícitos e preparação PostgreSQL/cloud." action={<div className="sync-actions"><button onClick={() => setDialog('create')}><HardDriveDownload /> Criar backup</button><button className="primary" onClick={() => void synchronize()} disabled={busy}><RefreshCw className={busy ? 'spin' : ''} /> Sincronizar agora</button></div>} />
    <Feedback error={error} />
    {summary && <section className="sync-summary-grid"><article><span className={online ? 'online' : 'offline'}>{online ? <Cloud /> : <CloudOff />}</span><p><small>Ligação</small><strong>{online ? 'Dispositivo online' : 'Modo offline'}</strong><em>{summary.remote_configured ? 'Servidor remoto configurado' : 'Checkpoint local ativo'}</em></p></article><article><span><UploadCloud /></span><p><small>Pendentes</small><strong>{summary.pending}</strong><em>Aguardam processamento</em></p></article><article><span className="warning"><AlertTriangle /></span><p><small>Conflitos / falhas</small><strong>{summary.conflicts + summary.failed}</strong><em>Requerem atenção</em></p></article><article><span><Database /></span><p><small>Última sincronização</small><strong>{summary.last_sync_at ? shortDate(summary.last_sync_at) : 'Nunca'}</strong><em>{summary.last_sync_status || summary.database}</em></p></article></section>}
    <div className="management-tabs"><button className={tab === 'queue' ? 'active' : ''} onClick={() => setTab('queue')}>Fila local</button><button className={tab === 'history' ? 'active' : ''} onClick={() => setTab('history')}>Histórico</button><button className={tab === 'backups' ? 'active' : ''} onClick={() => setTab('backups')}>Backups cifrados</button></div>
    {tab === 'queue' ? <section className="sync-list">{queue.map(item => <article key={item.id}><span className={item.status}><ArrowRightLeft /></span><div><small>{item.operation.toUpperCase()} · {item.entity_type}</small><strong>{item.entity_id}</strong><p>{item.error_message || `Registado em ${new Date(item.queued_at).toLocaleString('pt-AO')}`}</p></div><Status value={item.status} />{item.status === 'conflict' && <footer><button onClick={() => void resolve(item.id, 'remote')}>Usar remoto</button><button onClick={() => void resolve(item.id, 'local')}>Manter local</button></footer>}</article>)}</section> : tab === 'history' ? <section className="sync-list">{runs.map(item => <article key={item.id}><span className={item.status}><History /></span><div><small>{item.mode} · {new Date(item.started_at).toLocaleString('pt-AO')}</small><strong>{item.pushed_count} enviados · {item.pulled_count} recebidos</strong><p>{item.message}</p></div><Status value={item.status} /></article>)}</section> : <section className="backup-grid">{backups.map(item => <article key={item.id}><header><span><LockKeyhole /></span><Status value={item.status} /></header><small>{item.backup_no}</small><h2>{item.file_name}</h2><p>{(item.file_size / 1024 / 1024).toFixed(2)} MB · SHA-256 verificado</p><footer><button onClick={() => void api.downloadBackup(item.id, item.file_name)}><Download /> Exportar</button><button onClick={() => { setSelected(item); setDialog('restore') }}><RefreshCw /> Restaurar</button></footer></article>)}</section>}
    {dialog === 'create' && <Dialog title="Criar backup cifrado" onClose={() => setDialog(null)}><form className="module-form" onSubmit={submitBackup}><label>Palavra-passe do backup<input name="password" type="password" minLength={8} required placeholder="Mínimo de 8 caracteres" /></label><label>Notas<textarea name="notes" rows={3} placeholder="Ex.: Backup antes do fecho mensal" /></label><label className="check-field"><input name="include_files" type="checkbox" defaultChecked /> Incluir documentos, certificados e PDFs</label><footer><button type="button" onClick={() => setDialog(null)}>Cancelar</button><button className="primary" disabled={busy}><LockKeyhole /> Criar e cifrar</button></footer></form></Dialog>}
    {dialog === 'restore' && selected && <Dialog title={`Restaurar ${selected.backup_no}`} onClose={() => setDialog(null)}><form className="module-form" onSubmit={restore}><div className="danger-note"><AlertTriangle /><p><strong>Esta operação substitui a base local atual.</strong><span>O backup será verificado antes do restauro e o backend deverá ser reiniciado.</span></p></div><label>Palavra-passe do backup<input name="password" type="password" minLength={8} required /></label><footer><button type="button" onClick={() => setDialog(null)}>Cancelar</button><button className="danger" disabled={busy}><RefreshCw /> Confirmar restauro</button></footer></form></Dialog>}
  </>
}

export function SettingsPage() {
  const [records, setRecords] = useState<SystemSetting[]>([])
  const [mapStatus, setMapStatus] = useState<SystemMapStatus | null>(null)
  const [serpApi, setSerpApi] = useState<SerpApiStatus | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const load = useCallback(async () => {
    setError(null)
    try {
      const [settings, maps] = await Promise.all([api.settings(), api.mapStatus()])
      const typedMaps = maps as SystemMapStatus
      setRecords(settings)
      setMapStatus(typedMaps)
      const serpProvider = typedMaps.providers?.SERPAPI_PLACE_SEARCH
      if (serpProvider) {
        setSerpApi({
          provider: 'SERPAPI_GOOGLE_MAPS',
          status: serpProvider.status || (serpProvider.available ? 'DEGRADED' : 'NOT_CONFIGURED'),
          configured: Boolean(serpProvider.available),
          enabled: Boolean(serpProvider.available),
          message: serpProvider.message || 'Estado SerpApi disponível no backend.',
          checked_at: new Date().toISOString(),
          cache_ttl_seconds: serpProvider.cache_ttl_seconds || 0,
          rate_limit_per_minute: serpProvider.rate_limit_per_minute || 0,
          last_success_at: serpProvider.last_success_at,
          last_error: serpProvider.last_error,
          metrics: serpProvider.metrics || {},
        })
      }
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Não foi possível carregar as configurações.')
    }
  }, [])
  useEffect(() => { void load() }, [load])
  async function save(record: SystemSetting, value: string) { setBusy(record.id); setError(null); try { await api.updateSetting(record.id, value); await load() } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Não foi possível guardar a configuração.') } finally { setBusy(null) } }
  async function changeMapMode(mode: 'auto' | 'offline' | 'online') { setBusy('map-mode'); setError(null); try { setMapStatus(await api.setMapMode(mode) as SystemMapStatus) } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Não foi possível alterar o modo do mapa.') } finally { setBusy(null) } }
  async function testSerpApi() { setBusy('serpapi-test'); setError(null); try { const result = await api.testSerpApi(); setSerpApi(result); setMapStatus(await api.mapStatus() as SystemMapStatus) } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Não foi possível testar a SerpApi.') } finally { setBusy(null) } }
  const groups = useMemo(() => records.reduce<Record<string, SystemSetting[]>>((result, item) => { (result[item.category] ??= []).push(item); return result }, {}), [records])
  const providers = mapStatus?.providers ?? {}
  const google = providers.GOOGLE_ONLINE
  const mapLibre = providers.ONLINE_RASTER
  const offlineLabel = mapStatus?.active_package?.original_name || `${mapStatus?.packages?.length ?? 0} pacote(s) disponíveis`
  const activeProviderLabel = mapStatus?.active_provider === 'ONLINE_RASTER' ? 'MapLibre/OSM online' : mapStatus?.active_provider || 'Não definido'
  const serpStatus = serpApi?.status || providers.SERPAPI_PLACE_SEARCH?.status || 'NOT_CONFIGURED'
  return <>
    <Header eyebrow="Administração · Fase 13" title="Configurações empresariais" description="Políticas locais, segurança, mapas, geolocalização, integrações externas, backup e sincronização." />
    <Feedback error={error} />
    <section className="sync-summary-grid maps-geo-summary">
      <article><span className={mapStatus?.offline_active ? 'online' : ''}><MapPinned /></span><p><small>Provider ativo</small><strong>{activeProviderLabel}</strong><em>Modo {mapStatus?.mode || 'auto'} · padrão {mapStatus?.default_provider || 'ONLINE_RASTER'}</em></p></article>
      <article><span className={google?.configured ? 'online' : 'warning'}><Cloud /></span><p><small>Google Maps JS</small><strong>{google?.configured ? 'Chave configurada' : 'Não configurado'}</strong><em>{google?.configured ? 'Pronta para uso oficial no browser' : google?.reason || 'Defina VITE_GOOGLE_MAPS_API_KEY no frontend'}</em></p></article>
      <article><span className={mapLibre?.available ? 'online' : 'warning'}><Database /></span><p><small>MapLibre/OSM</small><strong>{mapLibre?.available ? 'Online disponível' : 'Indisponível'}</strong><em>{mapLibre?.style || mapLibre?.reason || 'Raster escuro com atribuição OSM/CARTO'}</em></p></article>
      <article><span className={mapStatus?.offline_active ? 'online' : 'offline'}><PackageCheck /></span><p><small>Offline PMTiles/MBTiles</small><strong>{mapStatus?.offline_active ? 'Ativo' : 'Em espera'}</strong><em>{offlineLabel}</em></p></article>
    </section>
    <section className="settings-grid maps-settings-grid">
      <article>
        <header><Search /><div><h2>Mapas e Geolocalização</h2><p>Health-check de providers, modo de fallback e pesquisa de locais.</p></div></header>
        <div className="setting-row"><div><strong>Modo do mapa</strong><small>Auto usa offline quando houver pacote ativo; online força MapLibre/Google conforme renderer.</small></div><label><select value={mapStatus?.mode || 'auto'} onChange={event => void changeMapMode(event.target.value as 'auto' | 'offline' | 'online')} disabled={busy === 'map-mode'}><option value="auto">Automático</option><option value="offline">Offline</option><option value="online">Online</option></select></label></div>
        <div className="setting-row"><div><strong>SerpApi Place Search</strong><small>{serpApi?.message || providers.SERPAPI_PLACE_SEARCH?.message || 'Teste a ligação sem expor a chave.'}</small></div><Status value={serpStatus === 'CONNECTED' ? 'pass' : serpStatus === 'NOT_CONFIGURED' ? 'warn' : 'fail'} /></div>
        <div className="setting-row"><div><strong>Última validação</strong><small>{serpApi?.checked_at ? new Date(serpApi.checked_at).toLocaleString('pt-AO') : 'Ainda não testada'} · cache {serpApi?.cache_ttl_seconds ?? providers.SERPAPI_PLACE_SEARCH?.cache_ttl_seconds ?? 0}s · limite {serpApi?.rate_limit_per_minute ?? providers.SERPAPI_PLACE_SEARCH?.rate_limit_per_minute ?? 0}/min</small></div><button className="module-secondary-button" onClick={() => void testSerpApi()} disabled={busy === 'serpapi-test'}><RefreshCw className={busy === 'serpapi-test' ? 'spin' : ''} /> Testar</button></div>
        {(serpApi?.last_error || providers.SERPAPI_PLACE_SEARCH?.last_error) && <div className="danger-note"><AlertTriangle /><p><strong>Último erro do provider</strong><span>{serpApi?.last_error || providers.SERPAPI_PLACE_SEARCH?.last_error}</span></p></div>}
      </article>
      <article>
        <header><ShieldCheck /><div><h2>Proteção de segredos</h2><p>As chaves ficam nos ficheiros locais ignorados pelo Git e nunca são apresentadas integralmente.</p></div></header>
        <div className="setting-row"><div><strong>Google Maps API key</strong><small>{google?.configured ? 'Configurada no ambiente frontend/backend; valor mascarado por segurança.' : 'Ausente no ambiente.'}</small></div><Status value={google?.configured ? 'pass' : 'warn'} /></div>
        <div className="setting-row"><div><strong>SerpApi key</strong><small>{serpApi?.configured || providers.SERPAPI_PLACE_SEARCH?.available ? 'Configurada no backend; valor mascarado por segurança.' : 'Ausente no backend.'}</small></div><Status value={serpApi?.configured || providers.SERPAPI_PLACE_SEARCH?.available ? 'pass' : 'warn'} /></div>
        <div className="setting-row"><div><strong>Auditoria</strong><small>Pesquisas e testes SerpApi gravam evento sem URL assinada nem API key.</small></div><Status value="pass" /></div>
      </article>
    </section>
    <section className="settings-grid">{Object.entries(groups).map(([category, items]) => <article key={category}><header><Settings2 /><div><h2>{category}</h2><p>{items?.length} parâmetros controlados</p></div></header>{items?.map(item => <SettingRow key={item.id} item={item} busy={busy === item.id} onSave={save} />)}</article>)}</section>
  </>
}

export function OpsReadinessPage() {
  const [report, setReport] = useState<ReadinessReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setReport(await api.readiness())
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Não foi possível carregar a prontidão operacional.')
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => { void load() }, [load])

  const commands = [
    { title: 'Preflight completo', command: '.\\scripts\\prod-preflight.ps1', detail: 'Compila backend, executa checks, testes e build do frontend.' },
    { title: 'Aplicar migrações', command: '.\\scripts\\migrate.ps1', detail: 'Marca/aplica o baseline Alembic antes do arranque produtivo.' },
    { title: 'Subir com Docker', command: 'docker compose up --build -d', detail: 'Usa volume persistente e healthcheck /ready.' },
  ]

  return <>
    <Header eyebrow="Produção · Fase 7" title="Produção & Saúde" description="Checklist operacional para instalar, validar e manter o ERP com mais segurança em ambiente real." action={<button className="module-primary-button" onClick={() => void load()} disabled={loading}><RefreshCw className={loading ? 'spin' : ''} /> Revalidar</button>} />
    <Feedback error={error} />
    {loading || !report ? <div className="module-loading"><RefreshCw className="spin" /> A validar ambiente...</div> : <>
      <section className="ops-readiness-hero">
        <article className={cn('readiness-state', report.status)}>
          <span><ShieldCheck /></span>
          <div><small>Estado geral</small><strong>{statusLabel[report.status]}</strong><p>{report.environment} · versão {report.version}</p></div>
        </article>
        <article><span><Check /></span><div><small>OK</small><strong>{report.summary.pass}</strong><p>Checks aprovados</p></div></article>
        <article><span><AlertTriangle /></span><div><small>Avisos</small><strong>{report.summary.warn}</strong><p>Requerem atenção</p></div></article>
        <article><span><X /></span><div><small>Falhas</small><strong>{report.summary.fail}</strong><p>Bloqueiam produção</p></div></article>
      </section>

      <section className="ops-meta-grid">
        <article><Database /><div><small>Base de dados</small><strong>{report.database}</strong></div></article>
        <article><Settings2 /><div><small>Schema automático</small><strong>{report.auto_create_schema ? 'Ativo' : 'Desativado'}</strong></div></article>
        <article><Cloud /><div><small>Frontend API</small><strong>{report.deployment.frontend_runtime}</strong></div></article>
        <article><History /><div><small>Gerado em</small><strong>{new Date(report.generated_at).toLocaleString('pt-AO')}</strong></div></article>
      </section>

      <section className="ops-check-grid">
        {report.checks.map(item => <article key={item.key} className={item.status}>
          <header><Status value={item.status} /><strong>{item.label}</strong></header>
          <p>{item.message}</p>
          {item.recommendation && <footer><ArrowRightLeft /> {item.recommendation}</footer>}
        </article>)}
      </section>

      <section className="ops-command-grid">
        {commands.map(item => <article key={item.command}>
          <header><Command /><div><h2>{item.title}</h2><p>{item.detail}</p></div></header>
          <code>{item.command}</code>
        </article>)}
      </section>
    </>}
  </>
}

function SettingRow({ item, busy, onSave }: { item: SystemSetting; busy: boolean; onSave: (item: SystemSetting, value: string) => Promise<void> }) {
  const [value, setValue] = useState(item.value)
  useEffect(() => setValue(item.value), [item.value])
  return <div className="setting-row"><div><strong>{item.label}</strong><small>{item.description}</small></div>{item.value_type === 'boolean' ? <button className={cn('setting-toggle', value === 'true' && 'on')} onClick={() => { const next = value === 'true' ? 'false' : 'true'; setValue(next); void onSave(item, next) }} aria-label={`Alterar ${item.label}`}><i /></button> : <label><input type={item.value_type === 'integer' ? 'number' : item.is_secret ? 'password' : 'text'} value={value} onChange={event => setValue(event.target.value)} /><button onClick={() => void onSave(item, value)} disabled={busy || value === item.value} aria-label={`Guardar ${item.label}`}><Save /></button></label>}</div>
}

export function PortalRequestsPage() {
  const [overview, setOverview] = useState<PortalOverview | null>(null)
  const [requests, setRequests] = useState<ServiceRequestRecord[]>([])
  const [equipment, setEquipment] = useState<Equipment[]>([])
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const load = useCallback(async () => { try { const [o, r, e] = await Promise.all([api.portalOverview(), api.portalRequests(), api.equipment()]); setOverview(o); setRequests(r); setEquipment(e) } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Não foi possível carregar o portal.') } }, [])
  useEffect(() => { void load() }, [load])
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setBusy(true); const data = new FormData(event.currentTarget); try { await api.createPortalRequest({ equipment_id: String(data.get('equipment_id') || '') || null, service_type: String(data.get('service_type')), preferred_date: String(data.get('preferred_date') || '') || null, location: String(data.get('location')), contact_name: String(data.get('contact_name')), contact_phone: String(data.get('contact_phone') || '') || null, priority: String(data.get('priority')), notes: String(data.get('notes') || '') || null }); setOpen(false); await load() } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Não foi possível submeter a solicitação.') } finally { setBusy(false) } }
  return <>
    <Header eyebrow="Portal da empresa · Fase 6" title="Solicitações de serviço" description="Peça inspeções, certificações e apoio técnico com acompanhamento transparente." action={<button className="module-primary-button" onClick={() => setOpen(true)}><Plus /> Nova solicitação</button>} />
    <Feedback error={error} />
    {overview && <section className="portal-summary"><article><PackageCheck /><p><strong>{overview.equipment_total}</strong><span>Equipamentos</span></p></article><article><FileCheck2 /><p><strong>{overview.certificates_valid}</strong><span>Certificados válidos</span></p></article><article><CalendarDays /><p><strong>{overview.requests_open}</strong><span>Pedidos em curso</span></p></article><article><CircleDollarSign /><p><strong>{money(overview.amount_due)}</strong><span>Saldo em aberto</span></p></article></section>}
    <section className="request-grid">{requests.map(item => <article key={item.id}><header><span><FileCheck2 /></span><Status value={item.status} /></header><small>{item.request_no} · {item.service_type}</small><h2>{item.equipment?.name || 'Serviço geral'}</h2><p>{item.location} · Preferência: {shortDate(item.preferred_date)}</p><div><span>Prioridade <b>{item.priority}</b></span><span>Pedido em <b>{shortDate(item.requested_date)}</b></span></div>{item.response_notes && <footer><Check /> {item.response_notes}</footer>}</article>)}</section>
    {open && <Dialog title="Nova solicitação de serviço" onClose={() => setOpen(false)}><form className="module-form two-columns" onSubmit={submit}><label>Tipo de serviço<select name="service_type"><option value="inspection">Inspeção técnica</option><option value="certification">Certificação</option><option value="maintenance">Manutenção</option><option value="consulting">Consultoria</option></select></label><label>Equipamento<select name="equipment_id"><option value="">Serviço geral</option>{equipment.map(item => <option value={item.id} key={item.id}>{item.code} · {item.name}</option>)}</select></label><label>Data preferida<input type="date" name="preferred_date" /></label><label>Prioridade<select name="priority"><option value="normal">Normal</option><option value="high">Alta</option><option value="urgent">Urgente</option><option value="low">Baixa</option></select></label><label className="full">Local do serviço<input name="location" required /></label><label>Nome de contacto<input name="contact_name" required /></label><label>Telefone<input name="contact_phone" /></label><label className="full">Observações<textarea name="notes" rows={4} /></label><footer className="full"><button type="button" onClick={() => setOpen(false)}>Cancelar</button><button className="primary" disabled={busy}><UploadCloud /> Submeter pedido</button></footer></form></Dialog>}
  </>
}

export function PortalBillingPage() {
  const [data, setData] = useState<PortalBilling | null>(null)
  const [tab, setTab] = useState<'invoices' | 'receipts'>('invoices')
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { api.portalBilling().then(setData).catch(reason => setError(reason instanceof ApiError ? reason.message : 'Não foi possível carregar a faturação.')) }, [])
  const due = data?.invoices.reduce((total, item) => total + Number(item.balance_due), 0) ?? 0
  return <>
    <Header eyebrow="Portal da empresa · Fase 6" title="Faturas & recibos" description="Acompanhe faturação, saldos, pagamentos e documentos financeiros emitidos." />
    <Feedback error={error} />
    {data && <section className="portal-summary"><article><FileText /><p><strong>{data.invoices.length}</strong><span>Faturas emitidas</span></p></article><article><ReceiptText /><p><strong>{data.receipts.length}</strong><span>Recibos</span></p></article><article><CircleDollarSign /><p><strong>{money(due)}</strong><span>Saldo por liquidar</span></p></article><article><ShieldCheck /><p><strong>100%</strong><span>Documentos verificados</span></p></article></section>}
    <div className="management-tabs"><button className={tab === 'invoices' ? 'active' : ''} onClick={() => setTab('invoices')}>Faturas</button><button className={tab === 'receipts' ? 'active' : ''} onClick={() => setTab('receipts')}>Recibos</button></div>
    {data && (tab === 'invoices' ? <section className="portal-billing-list">{data.invoices.map(item => <article key={item.id}><span><FileText /></span><div><small>{item.invoice_no}</small><strong>Emissão {shortDate(item.issue_date)} · Vencimento {shortDate(item.due_date)}</strong><p>Total {money(item.total_amount)} · Saldo {money(item.balance_due)}</p></div><Status value={item.status} /><button onClick={() => void api.downloadPortalInvoice(item.id, item.invoice_no)}><Download /> PDF</button></article>)}</section> : <section className="portal-billing-list">{data.receipts.map(item => <article key={item.id}><span><ReceiptText /></span><div><small>{item.receipt_no}</small><strong>Pagamento da {item.invoice.invoice_no}</strong><p>Emitido em {shortDate(item.issued_at)}</p></div><b>{money(item.amount)}</b><button onClick={() => void api.downloadPortalReceipt(item.id, item.receipt_no)}><Download /> PDF</button></article>)}</section>)}
  </>
}
