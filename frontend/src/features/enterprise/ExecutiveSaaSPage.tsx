import { useCallback, useEffect, useState } from 'react'
import { Cloud, Gauge, Plus, ShieldCheck } from 'lucide-react'

import { ErrorBanner, LoadingRows, PageHeader } from '@/pages/HRPages'
import { api, ApiError } from '@/services/api'
import type { ComplianceItem, ExecutiveBI, LicenseStatus } from '@/types'
import { dateLabel } from './formatters'
import { MetricCard } from './shared'

export function ExecutiveSaaSPage() {
  const [bi, setBi] = useState<ExecutiveBI | null>(null)
  const [compliance, setCompliance] = useState<ComplianceItem[]>([])
  const [license, setLicense] = useState<LicenseStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const load = useCallback(async () => {
    try {
      const [b, c, l] = await Promise.all([api.executiveBI(), api.compliance(), api.licenseStatus()])
      setBi(b)
      setCompliance(c)
      setLicense(l)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Falha ao carregar BI/SaaS.')
    }
  }, [])
  useEffect(() => { void load() }, [load])

  async function addCompliance() {
    await api.createCompliance({ code: `AUDIT-${Date.now().toString().slice(-5)}`, title: 'Evidência criada a partir do centro executivo', category: 'Auditoria', authority: 'FNLIFTING', risk_level: 'medium' })
    await load()
  }

  return <>
    <PageHeader eyebrow="Fase 12 · BI, Compliance & SaaS" title="Executive BI e prontidão SaaS" description="Indicadores consolidados, compliance documental, licenciamento modular e base para portal multiempresa." action={<button className="module-primary-button" onClick={() => void addCompliance()}><Plus /> Requisito compliance</button>} />
    {error && <ErrorBanner message={error} onRetry={load} />}
    {!bi ? <LoadingRows /> : <>
      <section className="phase-metrics-grid">{bi.scorecards.map(item => <MetricCard key={item.key} label={item.label} value={item.display} icon={Gauge} />)}</section>
      <section className="phase-two-column"><article className="phase-panel"><header><ShieldCheck /><div><h2>Compliance</h2><p>Risco executivo: {bi.risk.level}</p></div></header>{compliance.map(item => <div className="phase-row" key={item.id}><strong>{item.code}</strong><span>{item.title}</span><small>{item.risk_level} · {item.status} · {dateLabel(item.due_date)}</small></div>)}</article><article className="phase-panel"><header><Cloud /><div><h2>SaaS/licença</h2><p>{license?.company?.name}</p></div></header>{license?.license && <><div className="phase-row"><strong>{license.license.plan_code}</strong><span>{license.license.seats} utilizadores</span><small>{license.license.status}</small></div><div className="tag-cloud">{license.license.modules.map(item => <span key={item}>{item}</span>)}</div></>}</article></section>
    </>}
  </>
}
