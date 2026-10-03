import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Bell, Check, Cloud, Cpu, Fingerprint, LockKeyhole, ShieldCheck } from 'lucide-react'

import { ErrorBanner, LoadingRows, PageHeader } from '@/pages/HRPages'
import { api, ApiError } from '@/services/api'
import type { EnterpriseDevice, EnterpriseNotification, EnterpriseOverview, MfaSetup, SessionRecord } from '@/types'
import { dateLabel } from './formatters'
import { MetricCard } from './shared'

export function CloudSecurityPage() {
  const [overview, setOverview] = useState<EnterpriseOverview | null>(null)
  const [notifications, setNotifications] = useState<EnterpriseNotification[]>([])
  const [devices, setDevices] = useState<EnterpriseDevice[]>([])
  const [sessions, setSessions] = useState<SessionRecord[]>([])
  const [mfa, setMfa] = useState<MfaSetup | null>(null)
  const [recovery, setRecovery] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [o, n, s] = await Promise.all([api.enterpriseOverview(), api.enterpriseNotifications(), api.sessions()])
      setOverview(o)
      setNotifications(n)
      setSessions(s)
      try { setDevices(await api.enterpriseDevices()) } catch { setDevices([]) }
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Não foi possível carregar a segurança enterprise.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  async function registerDevice() {
    const deviceUid = localStorage.getItem('fnl_device_uid') ?? crypto.randomUUID()
    localStorage.setItem('fnl_device_uid', deviceUid)
    await api.registerDevice({ device_uid: deviceUid, name: navigator.userAgent.slice(0, 80), platform: 'web', app_version: overview?.version, capabilities: ['offline-cache', 'document-preview', 'mfa'] })
    await load()
  }

  async function setupMfa() {
    try {
      setMfa(await api.setupMfa())
      setRecovery([])
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Não foi possível iniciar MFA.')
    }
  }

  async function confirmMfa(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const code = String(new FormData(event.currentTarget).get('code') || '')
    try {
      const result = await api.confirmMfa(code)
      setRecovery(result.recovery_codes)
      setMfa(null)
      await load()
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Código MFA inválido.')
    }
  }

  return <>
    <PageHeader eyebrow="Fase 8 · Cloud & Segurança" title="Cloud, Sync 2.0, MFA e notificações" description="Camada local-first com dispositivos registados, MFA TOTP, sessões revogáveis e notificações auditáveis." action={<div className="page-header-actions"><button className="module-secondary-button" onClick={() => void api.generateEnterpriseNotifications().then(load)}><Bell /> Gerar alertas</button><button className="module-primary-button" onClick={() => void registerDevice()}><Cloud /> Registar dispositivo</button></div>} />
    {error && <ErrorBanner message={error} onRetry={load} />}
    {loading || !overview ? <LoadingRows /> : <>
      <section className="phase-metrics-grid">
        <MetricCard label="Modo de sync" value={overview.provider_mode} icon={Cloud} />
        <MetricCard label="Dispositivos" value={overview.metrics.registered_devices ?? 0} icon={Cpu} />
        <MetricCard label="Notificações" value={overview.metrics.unread_notifications ?? 0} icon={Bell} />
        <MetricCard label="MFA" value={overview.security.mfa_enabled ? 'Ativo' : 'Pendente'} icon={Fingerprint} />
      </section>
      <section className="phase-two-column">
        <article className="phase-panel"><header><LockKeyhole /><div><h2>MFA TOTP</h2><p>QR local, código temporário e códigos de recuperação.</p></div></header>{mfa ? <form className="module-form" onSubmit={confirmMfa}><img className="mfa-qr" src={mfa.qr_code_data_uri} alt="QR MFA" /><code>{mfa.secret}</code><label><span>Código de 6 dígitos</span><input name="code" required minLength={6} /></label><button className="module-primary-button"><Check /> Confirmar MFA</button></form> : <button className="module-primary-button" onClick={() => void setupMfa()}><Fingerprint /> Configurar MFA</button>}{recovery.length > 0 && <div className="recovery-grid">{recovery.map(item => <code key={item}>{item}</code>)}</div>}</article>
        <article className="phase-panel"><header><Cloud /><div><h2>Dispositivos</h2><p>Terminais autorizados e última presença.</p></div></header>{devices.map(item => <div className="phase-row" key={item.id}><strong>{item.name}</strong><span>{item.platform} · {item.status}</span><small>{dateLabel(item.last_seen_at)}</small></div>)}{!devices.length && <p>Registe este navegador para iniciar a lista de dispositivos.</p>}</article>
      </section>
      <section className="phase-two-column">
        <article className="phase-panel"><header><Bell /><div><h2>Notificações</h2><p>Centro in-app com delivery local.</p></div></header>{notifications.slice(0, 8).map(item => <button className="phase-row" key={item.id} onClick={() => void api.markNotificationRead(item.id).then(load)}><strong>{item.title}</strong><span>{item.message}</span><small>{item.level} · {item.status}</small></button>)}</article>
        <article className="phase-panel"><header><ShieldCheck /><div><h2>Sessões</h2><p>Revogação segura por utilizador.</p></div></header>{sessions.slice(0, 8).map(item => <div className="phase-row" key={item.id}><strong>{item.ip_address || 'Sessão local'}</strong><span>{item.status}</span><small>{dateLabel(item.created_at)}</small></div>)}</article>
      </section>
    </>}
  </>
}
