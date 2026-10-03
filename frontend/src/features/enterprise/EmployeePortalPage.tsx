import { useCallback, useEffect, useMemo, useState } from 'react'
import { Fingerprint, Network, ShieldCheck, Users, WalletCards } from 'lucide-react'

import { ErrorBanner, LoadingRows, PageHeader } from '@/pages/HRPages'
import { api, ApiError } from '@/services/api'
import type { EmployeePortal, OrgChart } from '@/types'
import { dateLabel, money } from './formatters'
import { MetricCard } from './shared'

export function EmployeePortalPage() {
  const [data, setData] = useState<EmployeePortal | null>(null)
  const [org, setOrg] = useState<OrgChart | null>(null)
  const [error, setError] = useState<string | null>(null)
  const period = useMemo(() => new Date().toISOString().slice(0, 7), [])
  const load = useCallback(async () => {
    try {
      const [portal, orgChart] = await Promise.all([api.employeePortal(), api.orgChart()])
      setData(portal)
      setOrg(orgChart)
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
    <PageHeader eyebrow="Fase 11 · RH Enterprise" title="Portal do trabalhador, organograma e payroll" description="Self-service, assiduidade, aprovacoes, hierarquia e processamento salarial." action={<button className="module-primary-button" onClick={() => void payroll()}><WalletCards /> Processar {period}</button>} />
    {error && <ErrorBanner message={error} onRetry={load} />}
    {!data ? <LoadingRows /> : <>
      <section className="phase-metrics-grid"><MetricCard label="Assiduidade" value={data.attendance.length} icon={Users} /><MetricCard label="Ferias/licencas" value={data.leave_requests.length} icon={ShieldCheck} /><MetricCard label="Payroll" value={data.payroll_runs.length} icon={WalletCards} /><MetricCard label="Posicoes" value={org?.summary.positions ?? 0} icon={Network} /></section>
      <section className="phase-two-column"><article className="phase-panel"><header><Users /><div><h2>Assiduidade</h2><p>Registos sujeitos a aprovacao.</p></div></header>{data.attendance.map(item => <div className="phase-row" key={item.id}><strong>{dateLabel(item.work_date)}</strong><span>{item.status}</span><small>{item.approval_status}</small></div>)}</article><article className="phase-panel"><header><WalletCards /><div><h2>Payroll</h2><p>Processamentos por periodo.</p></div></header>{data.payroll_runs.map(item => <div className="phase-row" key={item.id}><strong>{item.period}</strong><span>{money(item.net_total)}</span><small>{item.status}</small></div>)}</article></section>
      {org && <section className="phase-panel"><header><Network /><div><h2>Organograma</h2><p>Posicoes, departamentos, supervisores e ocupantes gerados a partir dos trabalhadores reais.</p></div></header>{org.positions.slice(0, 12).map(item => <div className="phase-row" key={item.id}><strong>{item.title}</strong><span>{item.employee?.full_name ?? 'vaga'} · {item.department?.name ?? 'sem departamento'}</span><small>Nivel {item.level} · {item.code}</small></div>)}</section>}
      <section className="phase-panel"><header><Fingerprint /><div><h2>Portal</h2><p>Identidade do trabalhador autenticado.</p></div></header><div className="phase-row"><strong>{data.employee?.full_name ?? 'Conta empresarial'}</strong><span>{data.employee?.job_title ?? 'Acesso corporativo'}</span><small>Self-service protegido por RBAC</small></div></section>
    </>}
  </>
}
