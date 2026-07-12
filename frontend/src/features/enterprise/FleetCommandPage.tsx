import { useCallback, useEffect, useState } from 'react'
import { Gauge, MapPin, Plus, ShieldCheck, Truck } from 'lucide-react'

import { ErrorBanner, LoadingRows, PageHeader } from '@/pages/HRPages'
import { api, ApiError } from '@/services/api'
import type { FleetCommandCenter } from '@/types'
import { dateLabel, MetricCard } from './shared'

export function FleetCommandPage() {
  const [data, setData] = useState<FleetCommandCenter | null>(null)
  const [error, setError] = useState<string | null>(null)
  const load = useCallback(async () => {
    try {
      setData(await api.fleetCommandCenter())
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Falha ao carregar command center.')
    }
  }, [])
  useEffect(() => { void load() }, [load])
  const firstTruck = data?.trucks[0]

  async function createCommand() {
    await api.createFleetCommand({ command_type: 'contact_driver', truck_id: firstTruck?.id, priority: 'high', payload: { reason: 'Validação operacional automática' } })
    await load()
  }

  async function ingestGps() {
    await api.ingestGps({ provider: 'local-gps', truck_id: firstTruck?.id, latitude: -8.839, longitude: 13.289, speed_kmh: 58, payload: { source: 'dashboard' } })
    await load()
  }

  return <>
    <PageHeader eyebrow="Fase 9 · Frota & GPS" title="Fleet command center" description="Comandos logísticos, ingestão GPS local e operação em tempo quase real para transporte e Oil & Gas." action={<div className="page-header-actions"><button className="module-secondary-button" onClick={() => void ingestGps()}><MapPin /> Ingerir GPS</button><button className="module-primary-button" onClick={() => void createCommand()} disabled={!firstTruck}><Plus /> Criar comando</button></div>} />
    {error && <ErrorBanner message={error} onRetry={load} />}
    {!data ? <LoadingRows /> : <>
      <section className="phase-metrics-grid"><MetricCard label="Camiões" value={data.summary.trucks ?? 0} icon={Truck} /><MetricCard label="Viagens ativas" value={data.summary.active_trips ?? 0} icon={Gauge} /><MetricCard label="Comandos abertos" value={data.summary.open_commands ?? 0} icon={ShieldCheck} /><MetricCard label="Eventos GPS" value={data.summary.gps_events ?? 0} icon={MapPin} /></section>
      <section className="phase-two-column"><article className="phase-panel"><header><Truck /><div><h2>Comandos</h2><p>Instruções operacionais abertas.</p></div></header>{data.commands.map(item => <div className="phase-row" key={item.id}><strong>{item.command_type}</strong><span>{item.priority} · {item.status}</span><small>{dateLabel(item.created_at)}</small></div>)}</article><article className="phase-panel"><header><MapPin /><div><h2>GPS</h2><p>Eventos de integração recebidos.</p></div></header>{data.gps_events.map(item => <div className="phase-row" key={item.id}><strong>{item.provider}</strong><span>{item.latitude}, {item.longitude}</span><small>{item.status}</small></div>)}</article></section>
    </>}
  </>
}
