import { useCallback, useEffect, useState } from 'react'
import { ClipboardCheck, Gauge, MapPin, Plus, ShieldCheck, Truck } from 'lucide-react'

import { ErrorBanner, LoadingRows, PageHeader } from '@/pages/HRPages'
import { api, ApiError } from '@/services/api'
import type { FleetCommandCenter, FleetComplianceCenter } from '@/types'
import { dateLabel, MetricCard } from './shared'

export function FleetCommandPage() {
  const [data, setData] = useState<FleetCommandCenter | null>(null)
  const [compliance, setCompliance] = useState<FleetComplianceCenter | null>(null)
  const [error, setError] = useState<string | null>(null)
  const load = useCallback(async () => {
    try {
      const [center, complianceCenter] = await Promise.all([api.fleetCommandCenter(), api.fleetCompliance()])
      setData(center)
      setCompliance(complianceCenter)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Falha ao carregar command center.')
    }
  }, [])
  useEffect(() => { void load() }, [load])
  const firstTruck = data?.trucks[0]

  async function createCommand() {
    await api.createFleetCommand({ command_type: 'contact_driver', truck_id: firstTruck?.id, priority: 'high', payload: { reason: 'Validacao operacional automatica' } })
    await load()
  }

  async function ingestGps() {
    await api.ingestGps({ provider: 'local-gps', truck_id: firstTruck?.id, latitude: -8.839, longitude: 13.289, speed_kmh: 58, payload: { source: 'dashboard' } })
    await load()
  }

  return <>
    <PageHeader eyebrow="Fase 9 · Frota & GPS" title="Fleet command center" description="Comandos logisticos, ingestao GPS local, compliance documental e operacao em tempo quase real." action={<div className="page-header-actions"><button className="module-secondary-button" onClick={() => void ingestGps()}><MapPin /> Ingerir GPS</button><button className="module-primary-button" onClick={() => void createCommand()} disabled={!firstTruck}><Plus /> Criar comando</button></div>} />
    {error && <ErrorBanner message={error} onRetry={load} />}
    {!data ? <LoadingRows /> : <>
      <section className="phase-metrics-grid"><MetricCard label="Camioes" value={data.summary.trucks ?? 0} icon={Truck} /><MetricCard label="Viagens ativas" value={data.summary.active_trips ?? 0} icon={Gauge} /><MetricCard label="Comandos abertos" value={data.summary.open_commands ?? 0} icon={ShieldCheck} /><MetricCard label="Docs a vencer" value={compliance?.summary.documents_expiring ?? 0} icon={ClipboardCheck} /></section>
      <section className="phase-two-column"><article className="phase-panel"><header><Truck /><div><h2>Comandos</h2><p>Instrucoes operacionais abertas.</p></div></header>{data.commands.map(item => <div className="phase-row" key={item.id}><strong>{item.command_type}</strong><span>{item.priority} · {item.status}</span><small>{dateLabel(item.created_at)}</small></div>)}</article><article className="phase-panel"><header><MapPin /><div><h2>GPS</h2><p>Eventos de integracao recebidos.</p></div></header>{data.gps_events.map(item => <div className="phase-row" key={item.id}><strong>{item.provider}</strong><span>{item.latitude}, {item.longitude}</span><small>{item.status}</small></div>)}</article></section>
      {compliance && <section className="phase-panel"><header><ClipboardCheck /><div><h2>Compliance da frota</h2><p>Documentos, tanques, reboques, manutencao e incidentes calculados a partir dos dados reais.</p></div></header>{compliance.items.slice(0, 8).map(item => <div className="phase-row" key={item.truck_id}><strong>{item.plate}</strong><span>{item.is_tanker ? `${item.tank_capacity_liters ?? 0}L` : item.truck_type} · {item.driver?.name ?? 'sem motorista'}</span><small>{item.documents.filter(doc => doc.status !== 'valid').length} alerta(s) documental(is) · {item.open_incidents} incidente(s)</small></div>)}</section>}
    </>}
  </>
}
