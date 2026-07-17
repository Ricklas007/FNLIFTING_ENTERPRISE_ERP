import { useCallback, useEffect, useState } from 'react'
import { Bot, BrainCircuit, CheckCircle2, Cpu, Sparkles, XCircle } from 'lucide-react'

import { ErrorBanner, LoadingRows, PageHeader } from '@/pages/HRPages'
import { api, ApiError } from '@/services/api'
import type { AIAssistantCenter, AutomationCenter } from '@/types'
import { MetricCard } from './shared'

export function AIAutomationPage() {
  const [center, setCenter] = useState<AutomationCenter | null>(null)
  const [assistant, setAssistant] = useState<AIAssistantCenter | null>(null)
  const [providers, setProviders] = useState<{ provider_type: string; provider_name: string; mode: string; status: string }[]>([])
  const [error, setError] = useState<string | null>(null)
  const load = useCallback(async () => {
    try {
      const [p, c, a] = await Promise.all([api.aiProviders(), api.automationCenter(), api.aiAssistant()])
      setProviders(p)
      setCenter(c)
      setAssistant(a)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Falha ao carregar automacao.')
    }
  }, [])
  useEffect(() => { void load() }, [load])

  async function createOcr() {
    await api.createOcrJob({ source_filename: `certificado-demo-${Date.now()}.pdf`, sample_text: 'Certificate No, Date, Inspector, Safe Working Load extraidos pelo OCR local.' })
    await api.generateAiAssistant()
    await load()
  }

  async function reviewSuggestion(id: string, status: 'accepted' | 'edited' | 'rejected', recommendation?: string) {
    await api.reviewAiSuggestion(id, { status, recommendation })
    await load()
  }

  return <>
    <PageHeader eyebrow="Fase 10 · IA & Automacao" title="OCR, regras e assistente local" description="Providers configuraveis, OCR com revisao humana, regras auditaveis e sugestoes aceites/editadas/descartadas." action={<button className="module-primary-button" onClick={() => void createOcr()}><Sparkles /> Novo OCR demo</button>} />
    {error && <ErrorBanner message={error} onRetry={load} />}
    {!center ? <LoadingRows /> : <>
      <section className="phase-metrics-grid"><MetricCard label="Providers" value={providers.length} icon={BrainCircuit} /><MetricCard label="Regras" value={center.rules.length} icon={Bot} /><MetricCard label="OCR jobs" value={center.ocr_jobs.length} icon={Sparkles} /><MetricCard label="Sugestoes pendentes" value={assistant?.summary.pending ?? 0} icon={Cpu} /></section>
      <section className="phase-two-column"><article className="phase-panel"><header><BrainCircuit /><div><h2>Providers</h2><p>Adapters locais/cloud.</p></div></header>{providers.map(item => <div className="phase-row" key={`${item.provider_type}-${item.provider_name}`}><strong>{item.provider_type}</strong><span>{item.provider_name} · {item.mode}</span><small>{item.status}</small></div>)}</article><article className="phase-panel"><header><Bot /><div><h2>Regras ativas</h2><p>Motor de automacao empresarial.</p></div></header>{center.rules.map(item => <div className="phase-row" key={item.id}><strong>{item.code}</strong><span>{item.name}</span><small>{item.module} · {item.severity}</small></div>)}</article></section>
      <section className="phase-panel"><header><Sparkles /><div><h2>Fila OCR</h2><p>Documentos extraidos e pendentes de revisao.</p></div></header>{center.ocr_jobs.map(item => <div className="phase-row" key={item.id}><strong>{item.source_filename}</strong><span>{item.status}</span><small>Confianca {Math.round((item.confidence ?? 0) * 100)}%</small></div>)}</section>
      {assistant && <section className="phase-panel"><header><Cpu /><div><h2>Assistente de decisoes</h2><p>Sugestoes persistidas com revisao humana obrigatoria.</p></div></header>{assistant.suggestions.slice(0, 10).map(item => <div className="phase-row" key={item.id}><strong>{item.title}</strong><span>{item.status} · {item.module}</span><small>{item.recommendation}</small>{item.status === 'pending' && <div className="phase-row-actions"><button onClick={() => void reviewSuggestion(item.id, 'accepted')}><CheckCircle2 /> Aceitar</button><button onClick={() => void reviewSuggestion(item.id, 'edited', `${item.recommendation} Revisado pelo operador.`)}><Sparkles /> Editar</button><button onClick={() => void reviewSuggestion(item.id, 'rejected')}><XCircle /> Descartar</button></div>}</div>)}</section>}
    </>}
  </>
}
