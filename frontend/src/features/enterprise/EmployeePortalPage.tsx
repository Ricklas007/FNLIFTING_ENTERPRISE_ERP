import { useCallback, useEffect, useMemo, useState } from 'react'
import { Fingerprint, ShieldCheck, Users, WalletCards } from 'lucide-react'

import { ErrorBanner, LoadingRows, PageHeader } from '@/pages/HRPages'
import { api, ApiError } from '@/services/api'
import type { EmployeePortal } from '@/types'
import { dateLabel, MetricCard, money } from './shared'

export function EmployeePortalPage() {
  const [data, setData] = useState<EmployeePortal | null>(null)
  const [error, setError] = useState<string | null>(null)
  const period = useMemo(() => new Date().toISOString().slice(0, 7), [])
  const load = useCallback(async () => {
    try {
      setData(await api.employeePortal())
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Falha ao carregar RH enterprise.')
    }
  }, [])
  useEffect(() => { void load() }, [load])

  async function payroll() {
    await api.createPayrollRun(period)
    await load()
  }

  return <>
    <PageHeader eyebrow="Fase 11 · RH Enterprise" title="Portal do trabalhador, assiduidade e payroll" description="Base para self-service, pedidos, assiduidade, aprovações e processamento salarial." action={<button className="module-primary-button" onClick={() => void payroll()}><WalletCards /> Processar {period}</button>} />
    {error && <ErrorBanner message={error} onRetry={load} />}
    {!data ? <LoadingRows /> : <>
      <section className="phase-metrics-grid"><MetricCard label="Assiduidade" value={data.attendance.length} icon={Users} /><MetricCard label="Férias/licenças" value={data.leave_requests.length} icon={ShieldCheck} /><MetricCard label="Payroll" value={data.payroll_runs.length} icon={WalletCards} /><MetricCard label="Portal" value={data.employee?.full_name ?? 'Empresa'} icon={Fingerprint} /></section>
      <section className="phase-two-column"><article className="phase-panel"><header><Users /><div><h2>Assiduidade</h2><p>Registos sujeitos a aprovação.</p></div></header>{data.attendance.map(item => <div className="phase-row" key={item.id}><strong>{dateLabel(item.work_date)}</strong><span>{item.status}</span><small>{item.approval_status}</small></div>)}</article><article className="phase-panel"><header><WalletCards /><div><h2>Payroll</h2><p>Processamentos por período.</p></div></header>{data.payroll_runs.map(item => <div className="phase-row" key={item.id}><strong>{item.period}</strong><span>{money(item.net_total)}</span><small>{item.status}</small></div>)}</article></section>
    </>}
  </>
}
