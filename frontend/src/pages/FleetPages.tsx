import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { AlertTriangle, CalendarClock, Fuel, Navigation, Plus, Radio, Route, Satellite, ShieldCheck, Star, Truck, UserRound } from 'lucide-react'

import { OfflineMapManager, RealFleetMap } from '@/components/RealFleetMap'
import { cn } from '@/lib/utils'
import { ErrorBanner, hasPermission, LoadingRows, Modal, PageHeader, SubmitButton } from '@/pages/HRPages'
import { api, ApiError } from '@/services/api'
import { useAuth } from '@/store/AuthContext'
import type { Client, Driver, FleetAlertRecord, FleetIncident, FleetSummary, GeofenceRecord, GPSPosition, GPSProviderHealth, GPSProviderRecord, GPSReplayData, TripRecord, TruckRecord } from '@/types'

const fleetLabels: Record<string, string> = {
  available: 'Disponível',
  on_trip: 'Em viagem',
  in_route: 'Em rota',
  maintenance: 'Manutenção',
  out_of_service: 'Fora de serviço',
  planned: 'Planeada',
  in_progress: 'Em andamento',
  delivered: 'Entregue',
  delayed: 'Atrasada',
  cancelled: 'Cancelada',
  incident: 'Com incidente',
  inactive: 'Inativo',
  suspended: 'Suspenso',
}
const today = new Date().toISOString().slice(0, 10)

function FleetStatus({ value }: { value: string }) {
  return <span className={cn('ops-status', value)}>{fleetLabels[value] ?? value}</span>
}

function expiring(value?: string) {
  if (!value) return false
  return (new Date(`${value}T00:00:00`).getTime() - Date.now()) / 86400000 < 60
}

function DriverForm({ onSaved, onClose }: { onSaved: () => Promise<void>; onClose: () => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    const data = Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>
    try {
      await api.createDriver({ ...data, rating: Number(data.rating) })
      await onSaved()
      onClose()
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Não foi possível guardar o motorista.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="module-form" onSubmit={submit}>
      {error && <ErrorBanner message={error} />}
      <div className="module-form-grid two">
        <label><span>Código</span><input name="driver_code" placeholder="DRV-2026-006" required /></label>
        <label><span>Nome completo</span><input name="full_name" required /></label>
        <label><span>N.º da carta</span><input name="license_number" required /></label>
        <label><span>Categoria</span><input name="license_category" defaultValue="D" required /></label>
        <label><span>Validade da carta</span><input name="license_expires_at" type="date" min={today} required /></label>
        <label><span>Telefone</span><input name="phone" /></label>
        <label><span>Avaliação</span><input name="rating" type="number" min="0" max="5" step="0.1" defaultValue="5" /></label>
        <label><span>Estado</span><select name="status" defaultValue="available"><option value="available">Disponível</option><option value="on_trip">Em viagem</option><option value="inactive">Inativo</option><option value="suspended">Suspenso</option></select></label>
      </div>
      <div className="module-form-actions">
        <button type="button" className="module-secondary-button" onClick={onClose}>Cancelar</button>
        <SubmitButton busy={busy}><UserRound /> Guardar motorista</SubmitButton>
      </div>
    </form>
  )
}

function TruckForm({ drivers, onSaved, onClose }: { drivers: Driver[]; onSaved: () => Promise<void>; onClose: () => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    const data = Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>
    try {
      await api.createTruck({
        ...data,
        manufacture_year: data.manufacture_year ? Number(data.manufacture_year) : null,
        tank_capacity_liters: data.tank_capacity_liters ? Number(data.tank_capacity_liters) : null,
        driver_id: data.driver_id || null,
      })
      await onSaved()
      onClose()
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Não foi possível guardar o camião.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="module-form" onSubmit={submit}>
      {error && <ErrorBanner message={error} />}
      <div className="module-form-grid three">
        <label><span>Matrícula</span><input name="plate" required /></label>
        <label><span>Marca</span><input name="brand" defaultValue="Volvo" required /></label>
        <label><span>Modelo</span><input name="model" required /></label>
        <label><span>Ano</span><input name="manufacture_year" type="number" min="1950" max="2100" /></label>
        <label><span>Tipo</span><select name="truck_type" defaultValue="fuel_tanker"><option value="fuel_tanker">Cisterna de combustível</option><option value="cargo">Carga</option><option value="support">Apoio</option></select></label>
        <label><span>Capacidade do tanque (L)</span><input name="tank_capacity_liters" type="number" min="1" /></label>
        <label><span>Chassis</span><input name="chassis_number" /></label>
        <label><span>Motorista atribuído</span><select name="driver_id" defaultValue=""><option value="">Sem atribuição</option>{drivers.map((item) => <option key={item.id} value={item.id}>{item.full_name}</option>)}</select></label>
        <label><span>Estado</span><select name="status" defaultValue="available"><option value="available">Disponível</option><option value="in_route">Em rota</option><option value="maintenance">Manutenção</option><option value="out_of_service">Fora de serviço</option></select></label>
        <label><span>Validade do seguro</span><input name="insurance_expires_at" type="date" /></label>
        <label><span>Validade da licença</span><input name="license_expires_at" type="date" /></label>
        <label><span>Inspeção técnica</span><input name="inspection_expires_at" type="date" /></label>
      </div>
      <div className="module-form-actions">
        <button type="button" className="module-secondary-button" onClick={onClose}>Cancelar</button>
        <SubmitButton busy={busy}><Truck /> Guardar camião</SubmitButton>
      </div>
    </form>
  )
}

export function FleetPage() {
  const { user } = useAuth()
  const canManage = hasPermission(user?.permissions ?? [], 'fleet.manage')
  const [summary, setSummary] = useState<FleetSummary | null>(null)
  const [drivers, setDrivers] = useState<Driver[]>([])
  const [trucks, setTrucks] = useState<TruckRecord[]>([])
  const [tab, setTab] = useState<'trucks' | 'drivers'>('trucks')
  const [modal, setModal] = useState<'truck' | 'driver' | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [sum, people, vehicles] = await Promise.all([api.fleetSummary(), api.drivers(), api.trucks()])
      setSummary(sum)
      setDrivers(people)
      setTrucks(vehicles)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Falha ao carregar a frota.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  return (
    <>
      <PageHeader eyebrow="Frota · Fase 4" title="Camiões e motoristas" description="Licenças, seguros, capacidade, atribuições e disponibilidade operacional." action={canManage && <div className="page-header-actions"><button className="module-secondary-button" onClick={() => setModal('driver')}><Plus /> Motorista</button><button className="module-primary-button" onClick={() => setModal('truck')}><Plus /> Camião</button></div>} />
      {error && <ErrorBanner message={error} onRetry={load} />}
      {summary && <section className="fleet-summary"><article><UserRound /><p>Motoristas<strong>{summary.drivers_total}</strong><small>{summary.drivers_available} disponíveis</small></p></article><article><Truck /><p>Camiões<strong>{summary.trucks_total}</strong><small>{summary.trucks_in_route} em rota</small></p></article><article><Route /><p>Viagens ativas<strong>{summary.trips_active}</strong><small>{summary.trips_delayed} atrasadas</small></p></article><article><Radio /><p>GPS online<strong>{summary.gps_online}</strong><small>{summary.open_incidents} incidente(s)</small></p></article></section>}
      <div className="fleet-tabs"><button className={tab === 'trucks' ? 'active' : ''} onClick={() => setTab('trucks')}>Camiões</button><button className={tab === 'drivers' ? 'active' : ''} onClick={() => setTab('drivers')}>Motoristas</button></div>
      {loading ? <LoadingRows /> : tab === 'trucks' ? (
        <section className="truck-grid">
          {trucks.map((item) => <article key={item.id}><header><span><Truck /></span><FleetStatus value={item.status} /></header><h2>{item.plate}</h2><p>{item.brand} {item.model} · {item.manufacture_year || 'Ano n/d'}</p><dl><div><dt>Capacidade</dt><dd>{item.tank_capacity_liters?.toLocaleString('pt-AO') || '—'} L</dd></div><div><dt>Motorista</dt><dd>{item.driver?.full_name || 'Sem atribuição'}</dd></div><div className={expiring(item.insurance_expires_at) ? 'warning' : ''}><dt>Seguro</dt><dd>{item.insurance_expires_at ? new Date(`${item.insurance_expires_at}T00:00:00`).toLocaleDateString('pt-AO') : '—'}</dd></div><div className={expiring(item.inspection_expires_at) ? 'warning' : ''}><dt>Inspeção</dt><dd>{item.inspection_expires_at ? new Date(`${item.inspection_expires_at}T00:00:00`).toLocaleDateString('pt-AO') : '—'}</dd></div></dl></article>)}
        </section>
      ) : (
        <section className="drivers-grid">
          {drivers.map((item) => <article key={item.id}><header><span>{item.full_name.split(' ').map((part) => part[0]).slice(0, 2).join('')}</span><FleetStatus value={item.status} /></header><h2>{item.full_name}</h2><p>{item.driver_code} · Categoria {item.license_category}</p><div><span><ShieldCheck /> {item.license_number}</span><span className={expiring(item.license_expires_at) ? 'warning' : ''}><CalendarClock /> {new Date(`${item.license_expires_at}T00:00:00`).toLocaleDateString('pt-AO')}</span><span><Star /> {Number(item.rating).toFixed(1)}</span></div></article>)}
        </section>
      )}
      {modal === 'driver' && <Modal title="Novo motorista" subtitle="Carta, contacto, categoria e disponibilidade." onClose={() => setModal(null)}><DriverForm onSaved={load} onClose={() => setModal(null)} /></Modal>}
      {modal === 'truck' && <Modal wide title="Novo camião" subtitle="Dados técnicos, documentos e motorista atribuído." onClose={() => setModal(null)}><TruckForm drivers={drivers} onSaved={load} onClose={() => setModal(null)} /></Modal>}
    </>
  )
}

function TripForm({ trucks, drivers, clients, onSaved, onClose }: { trucks: TruckRecord[]; drivers: Driver[]; clients: Client[]; onSaved: () => Promise<void>; onClose: () => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    const data = Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>
    try {
      await api.createTrip({
        ...data,
        client_id: data.client_id || null,
        quantity_liters: data.quantity_liters ? Number(data.quantity_liters) : null,
        departure_at: data.departure_at ? new Date(data.departure_at).toISOString() : null,
        expected_arrival_at: data.expected_arrival_at ? new Date(data.expected_arrival_at).toISOString() : null,
      })
      await onSaved()
      onClose()
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Não foi possível criar a viagem.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="module-form" onSubmit={submit}>
      {error && <ErrorBanner message={error} />}
      <div className="module-form-grid three">
        <label><span>Camião</span><select name="truck_id" required>{trucks.map((item) => <option key={item.id} value={item.id}>{item.plate} · {item.brand}</option>)}</select></label>
        <label><span>Motorista</span><select name="driver_id" required>{drivers.map((item) => <option key={item.id} value={item.id}>{item.full_name}</option>)}</select></label>
        <label><span>Cliente</span><select name="client_id" defaultValue=""><option value="">Operação interna</option>{clients.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label><span>Origem</span><input name="origin" defaultValue="Luanda" required /></label>
        <label><span>Destino</span><input name="destination" required /></label>
        <label><span>Província</span><input name="province" required /></label>
        <label><span>Cidade</span><input name="city" /></label>
        <label><span>Combustível</span><select name="fuel_type"><option>Gasóleo</option><option>Gasolina</option><option>Jet A-1</option></select></label>
        <label><span>Quantidade (L)</span><input name="quantity_liters" type="number" min="1" /></label>
        <label><span>Saída</span><input name="departure_at" type="datetime-local" /></label>
        <label><span>Chegada prevista</span><input name="expected_arrival_at" type="datetime-local" /></label>
        <label><span>Estado</span><select name="status" defaultValue="planned"><option value="planned">Planeada</option><option value="in_progress">Em andamento</option><option value="delayed">Atrasada</option></select></label>
        <label className="span-three"><span>Observações</span><textarea name="notes" rows={3} /></label>
      </div>
      <div className="module-form-actions">
        <button type="button" className="module-secondary-button" onClick={onClose}>Cancelar</button>
        <SubmitButton busy={busy}><Route /> Criar viagem</SubmitButton>
      </div>
    </form>
  )
}

export function TripsPage() {
  const { user } = useAuth()
  const canManage = hasPermission(user?.permissions ?? [], 'fleet.manage')
  const [trips, setTrips] = useState<TripRecord[]>([])
  const [positions, setPositions] = useState<GPSPosition[]>([])
  const [incidents, setIncidents] = useState<FleetIncident[]>([])
  const [trucks, setTrucks] = useState<TruckRecord[]>([])
  const [drivers, setDrivers] = useState<Driver[]>([])
  const [clients, setClients] = useState<Client[]>([])
  const [geofences, setGeofences] = useState<GeofenceRecord[]>([])
  const [alerts, setAlerts] = useState<FleetAlertRecord[]>([])
  const [providers, setProviders] = useState<GPSProviderRecord[]>([])
  const [providerHealth, setProviderHealth] = useState<Record<string, GPSProviderHealth>>({})
  const [selectedPosition, setSelectedPosition] = useState<GPSPosition | null>(null)
  const [replay, setReplay] = useState<GPSReplayData | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [tripRows, live, issueRows, vehicles, people, companies, fenceRows, alertRows, providerRows] = await Promise.all([
        api.trips(),
        api.livePositions(),
        api.incidents(),
        api.trucks(),
        api.drivers(),
        api.clients(),
        api.geofences(),
        api.fleetAlerts(),
        api.gpsProviders(),
      ])
      setTrips(tripRows)
      setPositions(live)
      setIncidents(issueRows)
      setTrucks(vehicles)
      setDrivers(people)
      setClients(companies)
      setGeofences(fenceRows)
      setAlerts(alertRows)
      setProviders(providerRows)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Falha ao carregar viagens e GPS.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  async function setStatus(item: TripRecord, status: string) {
    setBusyId(item.id)
    try {
      await api.updateTrip(item.id, { status })
      await load()
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Não foi possível atualizar a viagem.')
    } finally {
      setBusyId(null)
    }
  }

  async function loadReplay(item: TripRecord) {
    setBusyId(item.id)
    try {
      setReplay(await api.gpsReplay(`trip_id=${encodeURIComponent(item.id)}`))
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Não foi possível carregar o replay GPS.')
    } finally {
      setBusyId(null)
    }
  }

  async function resolveAlert(item: FleetAlertRecord) {
    setBusyId(item.id)
    try {
      await api.resolveFleetAlert(item.id)
      setAlerts(await api.fleetAlerts())
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Não foi possível resolver o alerta.')
    } finally {
      setBusyId(null)
    }
  }

  async function testProvider(item: GPSProviderRecord) {
    setBusyId(item.code)
    try {
      const result = await api.testGpsProvider(item.code)
      setProviderHealth((current) => ({ ...current, [item.code]: result }))
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Não foi possível testar o provider GPS.')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <>
      <PageHeader eyebrow="Frota · GPS" title="Viagens em tempo real" description="Planeamento, carga, rota, última posição conhecida e incidentes operacionais num mapa geográfico real." action={canManage && <button className="module-primary-button" onClick={() => setFormOpen(true)}><Plus /> Nova viagem</button>} />
      {error && <ErrorBanner message={error} onRetry={load} />}
      {loading ? <LoadingRows /> : (
        <>
          <div className="gps-layout">
            <section className="gps-map-panel">
              <header><div><Radio /><p><strong>Monitorização GPS</strong><small>{positions.length} camiões com sinal</small></p></div><span>MAPLIBRE</span></header>
              <RealFleetMap positions={positions} geofences={geofences} replay={replay} onMarkerClick={setSelectedPosition} />
              <footer>{positions.map((item) => <div key={item.id}><span><Truck /></span><p><strong>{item.truck.plate}</strong><small>{item.truck.driver?.full_name || 'Sem motorista'}</small></p><b>{Math.round(item.speed_kmh)} km/h</b><small>{new Date(item.recorded_at).toLocaleTimeString('pt-AO', { hour: '2-digit', minute: '2-digit' })}</small></div>)}</footer>
            </section>
            <aside className="trip-stream">
              <header><h2>Operações de transporte</h2><span>{trips.length} viagens</span></header>
              {trips.map((item) => <article key={item.id}><header><strong>{item.trip_code}</strong><FleetStatus value={item.status} /></header><div className="trip-route"><span>{item.origin}</span><i><Navigation /></i><span>{item.destination}</span></div><p><Truck /> {item.truck.plate}<span>·</span><UserRound /> {item.driver.full_name}</p><p><Fuel /> {item.fuel_type || 'Carga'} · {item.quantity_liters?.toLocaleString('pt-AO') || '—'} L</p><footer><button disabled={busyId === item.id} onClick={() => void loadReplay(item)}>Replay GPS</button>{canManage && item.status === 'planned' && <button disabled={busyId === item.id} onClick={() => void setStatus(item, 'in_progress')}>Iniciar viagem</button>}{canManage && item.status === 'in_progress' && <button disabled={busyId === item.id} onClick={() => void setStatus(item, 'delivered')}>Confirmar entrega</button>}</footer></article>)}
            </aside>
            <section className="incident-strip">
              <header><AlertTriangle /><p><strong>Incidentes e alertas</strong><small>Acompanhamento operacional</small></p></header>
              {incidents.length ? incidents.map((item) => <article key={item.id}><FleetStatus value={item.status} /><strong>{item.incident_type}</strong><span>{item.location}</span><p>{item.description}</p></article>) : <p>Sem incidentes ativos.</p>}
            </section>
          </div>
          <section className="gps-command-center-strip">
            <article><header><Navigation /><p><strong>{selectedPosition ? selectedPosition.truck.plate : 'Replay carregado'}</strong><small>{selectedPosition ? `${selectedPosition.latitude.toFixed(5)}, ${selectedPosition.longitude.toFixed(5)} · ${Math.round(selectedPosition.speed_kmh)} km/h` : replay ? `${replay.count} ponto(s), ${replay.stops.length} paragem(ns)` : 'Selecione uma viagem ou camião no mapa.'}</small></p></header>{replay && <button className="module-secondary-button" onClick={() => setReplay(null)}>Limpar replay</button>}</article>
            <article><header><AlertTriangle /><p><strong>Alertas abertos</strong><small>{alerts.length} evento(s) por resolver</small></p></header>{alerts.slice(0, 4).map((item) => <button key={item.id} className="fleet-alert-pill" onClick={() => void resolveAlert(item)}><span>{item.severity}</span>{item.title}</button>)}</article>
            <article><header><Radio /><p><strong>Geofences ativas</strong><small>{geofences.filter((item) => item.status === 'active').length} área(s)</small></p></header>{geofences.slice(0, 4).map((item) => <span key={item.id} className="geofence-pill">{item.geofence_type} · {item.name}</span>)}</article>
            <article><header><Satellite /><p><strong>Integrações GPS</strong><small>{providers.length} provider(s) registado(s)</small></p></header>{providers.slice(0, 5).map((item) => <button key={item.code} className="fleet-alert-pill" disabled={busyId === item.code || (!canManage && item.status !== 'CONNECTED')} onClick={() => canManage ? void testProvider(item) : undefined}><span>{providerHealth[item.code]?.status || item.status}</span>{item.name}</button>)}</article>
          </section>
          <OfflineMapManager />
        </>
      )}
      {formOpen && <Modal wide title="Nova viagem" subtitle="Associe camião, motorista, cliente, carga e janela operacional." onClose={() => setFormOpen(false)}><TripForm trucks={trucks} drivers={drivers} clients={clients} onSaved={load} onClose={() => setFormOpen(false)} /></Modal>}
    </>
  )
}
