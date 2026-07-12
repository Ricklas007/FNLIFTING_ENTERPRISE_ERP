import { useCallback, useEffect, useState } from 'react'
import { Bot, BrainCircuit, Cpu, Sparkles } from 'lucide-react'

import { ErrorBanner, LoadingRows, PageHeader } from '@/pages/HRPages'
import { api, ApiError } from '@/services/api'
import type { AutomationCenter } from '@/types'
import { MetricCard } from './shared'

export function AIAutomationPage() {
  const [center, setCenter] = useState<AutomationCenter | null>(null)
  const [providers, setProviders] = useState<{ provider_type: string; provider_name: string; mode: string; status: string }[]>([])
  const [error, setError] = useState<string | null>(null)
  const load = useCallback(async () => {
    try {
      const [p, c] = await Promise.all([api.aiProviders(), api.automationCenter()])
      setProviders(p)
      setCenter(c)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Falha ao carregar automação.')
    }
  }, [])
  useEffect(() => { void load() }, [load])

  async function createOcr() {
    await api.createOcrJob({ source_filename: `certificado-demo-${Date.now()}.pdf`, sample_text: 'Certificate No, Date, Inspector, Safe Working Load extraídos pelo OCR local.' })
    await load()
  }

  return <>
    <PageHeader eyebrow="Fase 10 · IA & Automação" title="OCR, regras e agentes locais" description="Providers configuráveis, OCR com revisão humana e regras automáticas auditáveis." action={<button className="module-primary-button" onClick={() => void createOcr()}><Sparkles /> Novo OCR demo</button>} />
    {error && <ErrorBanner message={error} onRetry={load} />}
    {!center ? <LoadingRows /> : <>
      <section className="phase-metrics-grid"><MetricCard label="Providers" value={providers.length} icon={BrainCircuit} /><MetricCard label="Regras" value={center.rules.length} icon={Bot} /><MetricCard label="OCR jobs" value={center.ocr_jobs.length} icon={Sparkles} /><MetricCard label="Execuções" value={center.runs.length} icon={Cpu} /></section>
      <section className="phase-two-column"><article className="phase-panel"><header><BrainCircuit /><div><h2>Providers</h2><p>Adapters locais/cloud.</p></div></header>{providers.map(item => <div className="phase-row" key={`${item.provider_type}-${item.provider_name}`}><strong>{item.provider_type}</strong><span>{item.provider_name} · {item.mode}</span><small>{item.status}</small></div>)}</article><article className="phase-panel"><header><Bot /><div><h2>Regras ativas</h2><p>Motor de automação empresarial.</p></div></header>{center.rules.map(item => <div className="phase-row" key={item.id}><strong>{item.code}</strong><span>{item.name}</span><small>{item.module} · {item.severity}</small></div>)}</article></section>
      <section className="phase-panel"><header><Sparkles /><div><h2>Fila OCR</h2><p>Documentos extraídos e pendentes de revisão.</p></div></header>{center.ocr_jobs.map(item => <div className="phase-row" key={item.id}><strong>{item.source_filename}</strong><span>{item.status}</span><small>Confiança {Math.round((item.confidence ?? 0) * 100)}%</small></div>)}</section>
    </>}
  </>
}
