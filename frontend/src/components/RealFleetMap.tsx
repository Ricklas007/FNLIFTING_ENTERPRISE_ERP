import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { Database, Map, RefreshCw, Trash2, Truck } from 'lucide-react'

import { api, ApiError, apiUrl, tokenStore } from '@/services/api'
import type { GeofenceRecord, GPSPosition, GPSReplayData } from '@/types'

declare global {
  interface Window {
    maplibregl?: any
    pmtiles?: any
  }
}

type MapMode = 'auto' | 'offline' | 'online'

type MapPackage = {
  id: string
  provider: 'OFFLINE_PMTILES' | 'OFFLINE_MBTILES'
  original_name: string
  size_bytes: number
  checksum_sha256: string
  source?: string
  license?: string
  version?: string
  bounds?: number[] | string | null
  min_zoom?: number | null
  max_zoom?: number | null
  tile_format?: string | null
  imported_at?: string
}

type MapStatus = {
  mode: MapMode
  active_package?: MapPackage | null
  packages: MapPackage[]
  storage: { map_dir: string; cache_dir: string; free_bytes?: number; total_bytes?: number }
  angola_view?: { center?: [number, number]; bounds?: [number, number, number, number] }
}

const MAPLIBRE_JS = 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js'
const MAPLIBRE_CSS = 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css'
const PMTILES_JS = 'https://unpkg.com/pmtiles@3.2.1/dist/pmtiles.js'
const RASTER_TILE_FORMATS = new Set(['png', 'jpg', 'jpeg', 'webp', 'unknown', undefined, null])

function loadCss(href: string) {
  if (document.querySelector(`link[href="${href}"]`)) return
  const link = document.createElement('link')
  link.rel = 'stylesheet'
  link.href = href
  document.head.appendChild(link)
}

function loadScript(src: string) {
  return new Promise<void>((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) return resolve()
    const script = document.createElement('script')
    script.src = src
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error(`Falha ao carregar ${src}`))
    document.head.appendChild(script)
  })
}

function formatBytes(value?: number) {
  if (!value && value !== 0) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = value
  let index = 0
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024
    index += 1
  }
  return `${size.toFixed(index ? 1 : 0)} ${units[index]}`
}

function onlineRasterStyle() {
  return {
    version: 8,
    sources: {
      osm: {
        type: 'raster',
        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
        tileSize: 256,
        attribution: '© OpenStreetMap contributors',
      },
    },
    layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
  }
}

function mbtilesRasterStyle(packageId: string, attribution?: string) {
  return {
    version: 8,
    sources: {
      offline: {
        type: 'raster',
        tiles: [apiUrl(`/maps/packages/${packageId}/tiles/{z}/{x}/{y}.png`)],
        tileSize: 256,
        attribution: attribution || 'Offline MBTiles importado pelo cliente',
      },
    },
    layers: [{ id: 'offline', type: 'raster', source: 'offline' }],
  }
}

function fallbackPosition(position: GPSPosition) {
  const x = Math.max(6, Math.min(94, ((position.longitude - 11) / 13) * 100))
  const y = Math.max(6, Math.min(94, ((-4 - position.latitude) / 14) * 100))
  return { left: `${x}%`, top: `${y}%` }
}

function circlePolygon(center: [number, number], radiusMeters: number) {
  const points: [number, number][] = []
  const earth = 6371000
  const lat = center[1] * Math.PI / 180
  const lon = center[0] * Math.PI / 180
  for (let index = 0; index <= 64; index += 1) {
    const bearing = (index / 64) * Math.PI * 2
    const angular = radiusMeters / earth
    const pointLat = Math.asin(Math.sin(lat) * Math.cos(angular) + Math.cos(lat) * Math.sin(angular) * Math.cos(bearing))
    const pointLon = lon + Math.atan2(Math.sin(bearing) * Math.sin(angular) * Math.cos(lat), Math.cos(angular) - Math.sin(lat) * Math.sin(pointLat))
    points.push([pointLon * 180 / Math.PI, pointLat * 180 / Math.PI])
  }
  return [points]
}

function geofenceFeature(item: GeofenceRecord) {
  const geometry = item.geometry || {}
  const raw = (geometry.center || geometry.coordinates) as unknown
  if ((item.shape_type === 'circle' || item.shape_type === 'point') && Array.isArray(raw) && raw.length >= 2) {
    return {
      type: 'Feature',
      geometry: { type: 'Polygon', coordinates: circlePolygon([Number(raw[0]), Number(raw[1])], item.radius_meters || Number((geometry as Record<string, unknown>).radius_meters) || 75) },
      properties: { name: item.name, geofence_type: item.geofence_type, shape_type: item.shape_type },
    }
  }
  if (Array.isArray(raw)) {
    const coordinates = Array.isArray(raw[0]?.[0]) ? raw : [raw]
    return { type: 'Feature', geometry: { type: 'Polygon', coordinates }, properties: { name: item.name, geofence_type: item.geofence_type, shape_type: item.shape_type } }
  }
  return null
}

function chooseInitialProvider(status: MapStatus) {
  const active = status.active_package
  if (status.mode === 'offline') return active ? 'offline' : 'unavailable'
  if (status.mode === 'online') return 'online'
  return navigator.onLine === false && active ? 'offline' : 'online'
}

function offlineStyle(active: MapPackage) {
  if (active.provider === 'OFFLINE_MBTILES') {
    if (!RASTER_TILE_FORMATS.has(active.tile_format)) {
      throw new Error(`MBTiles ${active.tile_format} precisa de stylesheet vectorial antes de renderizar.`)
    }
    return mbtilesRasterStyle(active.id, active.license)
  }
  throw new Error('PMTiles importado: provider preparado, mas exige stylesheet/layers do pacote antes de renderizar.')
}

export function RealFleetMap({ positions, geofences = [], replay = null, onMarkerClick }: { positions: GPSPosition[]; geofences?: GeofenceRecord[]; replay?: GPSReplayData | null; onMarkerClick?: (position: GPSPosition) => void }) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<any>(null)
  const markersRef = useRef<any[]>([])
  const [mapReady, setMapReady] = useState(0)
  const [status, setStatus] = useState<MapStatus | null>(null)
  const [providerLabel, setProviderLabel] = useState('ONLINE_RASTER')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function boot() {
      try {
        const mapStatus = await api.mapStatus() as MapStatus
        if (cancelled) return
        setStatus(mapStatus)
        loadCss(MAPLIBRE_CSS)
        await loadScript(MAPLIBRE_JS)
        if (!window.maplibregl || !containerRef.current || cancelled) return

        const active = mapStatus.active_package
        const selected = chooseInitialProvider(mapStatus)
        let style: any = onlineRasterStyle()
        if (selected === 'offline') {
          if (!active) throw new Error('Nenhum pacote offline ativo.')
          if (active.provider === 'OFFLINE_PMTILES') await loadScript(PMTILES_JS)
          style = offlineStyle(active)
          setProviderLabel(active.provider)
        } else if (selected === 'unavailable') {
          throw new Error('Nenhum provider de mapa disponível.')
        } else {
          setProviderLabel('ONLINE_RASTER')
        }

        const token = tokenStore.access()
        mapRef.current = new window.maplibregl.Map({
          container: containerRef.current,
          style,
          center: mapStatus.angola_view?.center ?? [17.8739, -11.2027],
          zoom: 5,
          maxBounds: mapStatus.angola_view?.bounds,
          transformRequest: (url: string) => {
            if (url.includes('/api/v1/') && token) return { url, headers: { Authorization: `Bearer ${token}` } }
            return { url }
          },
        })
        mapRef.current.addControl(new window.maplibregl.NavigationControl({ visualizePitch: true }), 'top-right')
        mapRef.current.on('load', () => setMapReady(Date.now()))
        let switchedToOffline = false
        mapRef.current.on('error', () => {
          if (mapStatus.mode !== 'auto' || !active || switchedToOffline || selected !== 'online') return
          try {
            switchedToOffline = true
            mapRef.current.setStyle(offlineStyle(active))
            setProviderLabel(`${active.provider} fallback`)
          } catch (reason) {
            setError(reason instanceof Error ? reason.message : 'Mapa offline indisponível')
          }
        })
      } catch (reason) {
        if (!cancelled) setError(reason instanceof Error ? reason.message : 'Mapa indisponível')
      }
    }
    void boot()
    return () => {
      cancelled = true
      markersRef.current.forEach((marker) => marker.remove())
      markersRef.current = []
      if (mapRef.current) mapRef.current.remove()
      mapRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!mapRef.current || !window.maplibregl) return
    markersRef.current.forEach((marker) => marker.remove())
    markersRef.current = positions.map((position) => {
      const element = document.createElement('button')
      element.className = 'gps-marker real'
      element.type = 'button'
      element.title = `${position.truck.plate} · ${Math.round(position.speed_kmh)} km/h`
      element.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 17h4v2h-4z"/><path d="M4 6h12l4 5v6h-2a3 3 0 0 1-6 0H9a3 3 0 0 1-6 0H1V9a3 3 0 0 1 3-3z"/></svg><i></i>'
      element.addEventListener('click', () => onMarkerClick?.(position))
      return new window.maplibregl.Marker({ element }).setLngLat([position.longitude, position.latitude]).addTo(mapRef.current)
    })
  }, [positions, onMarkerClick])

  useEffect(() => {
    if (!mapRef.current || !window.maplibregl || !mapReady) return
    const map = mapRef.current
    const features = geofences.map(geofenceFeature).filter(Boolean)
    const geofenceSource = { type: 'FeatureCollection', features }
    if (map.getSource('fnl-geofences')) {
      map.getSource('fnl-geofences').setData(geofenceSource)
    } else {
      map.addSource('fnl-geofences', { type: 'geojson', data: geofenceSource })
      map.addLayer({ id: 'fnl-geofences-fill', type: 'fill', source: 'fnl-geofences', paint: { 'fill-color': '#1d9bf0', 'fill-opacity': 0.12 } })
      map.addLayer({ id: 'fnl-geofences-line', type: 'line', source: 'fnl-geofences', paint: { 'line-color': '#38bdf8', 'line-width': 2, 'line-dasharray': [2, 1] } })
    }

    const coordinates = replay?.positions?.map((point) => [point.longitude, point.latitude]) ?? []
    const replaySource = {
      type: 'FeatureCollection',
      features: coordinates.length >= 2 ? [{ type: 'Feature', geometry: { type: 'LineString', coordinates }, properties: { count: coordinates.length } }] : [],
    }
    if (map.getSource('fnl-replay')) {
      map.getSource('fnl-replay').setData(replaySource)
    } else {
      map.addSource('fnl-replay', { type: 'geojson', data: replaySource })
      map.addLayer({ id: 'fnl-replay-line', type: 'line', source: 'fnl-replay', paint: { 'line-color': '#f59e0b', 'line-width': 4, 'line-opacity': 0.78 } })
    }
  }, [geofences, replay, mapReady])

  return (
    <div className="real-map-shell">
      <div ref={containerRef} className="real-map-container" />
      {(error || !window.maplibregl) && (
        <div className="map-fallback-overlay">
          <strong>{error ? 'Mapa real indisponível' : 'A carregar MapLibre GL JS'}</strong>
          <span>Provider: {status?.active_package ? status.active_package.provider : 'ONLINE_RASTER / fallback'}</span>
          <div className="angola-map fallback-only">
            {positions.map((position) => (
              <button key={position.id} className="gps-marker" style={fallbackPosition(position)} title={`${position.truck.plate} · ${position.speed_kmh} km/h`} onClick={() => onMarkerClick?.(position)}>
                <Truck /><i />
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="map-legend real">
        <span><i /> GPS em tempo real</span>
        <span><i /> {providerLabel}</span>
        <span><i /> {geofences.length} geofence(s)</span>
      </div>
    </div>
  )
}

export function OfflineMapManager() {
  const [status, setStatus] = useState<MapStatus | null>(null)
  const [sourcePath, setSourcePath] = useState('')
  const [mode, setMode] = useState<MapMode>('auto')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const next = await api.mapStatus() as MapStatus
      setStatus(next)
      setMode(next.mode)
      setError(null)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Não foi possível carregar os mapas.')
    }
  }, [])

  useEffect(() => { void load() }, [load])

  async function importPackage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    const form = new FormData(event.currentTarget)
    try {
      await api.importMapPackage({
        source_path: sourcePath,
        activate: form.get('activate') === 'on',
        source: form.get('source') || 'manual',
        license: form.get('license') || 'unknown',
        version: form.get('version') || 'unknown',
      })
      setSourcePath('')
      await load()
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Não foi possível importar o pacote de mapa.')
    } finally {
      setBusy(false)
    }
  }

  async function changeMode(nextMode: MapMode) {
    setMode(nextMode)
    setBusy(true)
    try {
      const next = await api.setMapMode(nextMode) as MapStatus
      setStatus(next)
      setError(null)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Não foi possível alterar o modo do mapa.')
    } finally {
      setBusy(false)
    }
  }

  async function activate(id: string) {
    setBusy(true)
    try {
      await api.activateMapPackage(id)
      await load()
    } finally {
      setBusy(false)
    }
  }

  async function remove(id: string) {
    if (!window.confirm('Remover este pacote offline do userData\\maps?')) return
    setBusy(true)
    try {
      await api.removeMapPackage(id)
      await load()
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="offline-map-manager">
      <header>
        <div><Map /><p><strong>Gestor de mapas offline</strong><small>{status?.storage.map_dir || 'A carregar localização...'}</small></p></div>
        <button className="module-secondary-button" disabled={busy} onClick={() => void load()}><RefreshCw className={busy ? 'spin' : ''} /> Atualizar</button>
      </header>
      {error && <p className="map-manager-error">{error}</p>}
      <div className="map-manager-controls">
        <label><span>Modo</span><select value={mode} onChange={(event) => void changeMode(event.target.value as MapMode)}><option value="auto">Auto: online com fallback offline</option><option value="online">Online raster</option><option value="offline">Offline local</option></select></label>
        <span>Espaço livre: <strong>{formatBytes(status?.storage.free_bytes)}</strong></span>
        <span>Ativo: <strong>{status?.active_package?.original_name || 'sem pacote offline'}</strong></span>
      </div>
      <form className="map-import-form" onSubmit={importPackage}>
        <label className="span-three"><span>Caminho local PMTiles/MBTiles</span><input value={sourcePath} onChange={(event) => setSourcePath(event.target.value)} placeholder="C:\\Mapas\\angola.mbtiles ou C:\\Mapas\\angola.pmtiles" required /></label>
        <label><span>Fonte</span><input name="source" placeholder="OSM / fornecedor licenciado" /></label>
        <label><span>Licença</span><input name="license" placeholder="ODbL / licença contratada" /></label>
        <label><span>Versão</span><input name="version" placeholder="2026-07" /></label>
        <label className="checkbox-line"><input name="activate" type="checkbox" defaultChecked /> Ativar após importar</label>
        <button className="module-primary-button" disabled={busy || !sourcePath}><Database /> Importar pacote</button>
      </form>
      <div className="map-package-list">
        {status?.packages.length ? status.packages.map((item) => (
          <article key={item.id} className={status.active_package?.id === item.id ? 'active' : ''}>
            <div><strong>{item.original_name}</strong><span>{item.provider} · {item.tile_format || 'formato n/d'} · {formatBytes(item.size_bytes)}</span><small>SHA256 {item.checksum_sha256.slice(0, 16)}… · {item.source || 'manual'} · {item.license || 'licença n/d'}</small></div>
            <div><button className="module-secondary-button" disabled={busy || status.active_package?.id === item.id} onClick={() => void activate(item.id)}>Ativar</button><button className="icon-danger" disabled={busy} onClick={() => void remove(item.id)} title="Remover"><Trash2 /></button></div>
          </article>
        )) : <p className="empty-map-packages">Sem pacotes offline importados. O mapa online usa OpenStreetMap raster quando houver ligação.</p>}
      </div>
    </section>
  )
}
