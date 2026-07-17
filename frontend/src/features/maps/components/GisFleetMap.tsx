import 'maplibre-gl/dist/maplibre-gl.css'

import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import maplibregl, { type Map as MapLibreMap, type Marker } from 'maplibre-gl'
import { Protocol } from 'pmtiles'
import { AlertTriangle, Database, Map, MapPin, RefreshCw, Satellite, Trash2, Truck } from 'lucide-react'

import { api, ApiError, tokenStore } from '@/services/api'
import type { GeofenceRecord, GPSPosition, GPSReplayData, MapPlaceResult } from '@/types'

import { offlineFallbackProvider, resolveMapProvider } from '../providers/mapProvider'
import { GoogleMapsOnlineProvider } from '../providers/GoogleMapsOnlineProvider'
import { onlineRasterStyle, styleForOfflinePackage } from '../providers/mapStyles'
import type { MapMode, MapPackage, MapStatus, ResolvedMapProvider } from '../types'

let pmtilesProtocolInstalled = false

function ensurePmtilesProtocol() {
  if (pmtilesProtocolInstalled) return
  const protocol = new Protocol()
  maplibregl.addProtocol('pmtiles', protocol.tile as Parameters<typeof maplibregl.addProtocol>[1])
  pmtilesProtocolInstalled = true
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

function styleForProvider(provider: ResolvedMapProvider) {
  if (provider.kind === 'ONLINE_RASTER') return onlineRasterStyle()
  if ((provider.kind === 'OFFLINE_MBTILES' || provider.kind === 'OFFLINE_PMTILES') && provider.package) {
    if (provider.kind === 'OFFLINE_PMTILES') ensurePmtilesProtocol()
    return styleForOfflinePackage(provider.package)
  }
  throw new Error(provider.reason || 'Nenhum provider cartográfico real está disponível.')
}

function removeLayers(map: MapLibreMap, ids: string[]) {
  ids.forEach((id) => {
    if (map.getLayer(id)) map.removeLayer(id)
  })
}

function removeSources(map: MapLibreMap, ids: string[]) {
  ids.forEach((id) => {
    if (map.getSource(id)) map.removeSource(id)
  })
}

function setMapData(map: MapLibreMap, sourceId: string, data: maplibregl.GeoJSONSourceSpecification['data']) {
  const source = map.getSource(sourceId) as maplibregl.GeoJSONSource | undefined
  if (source) source.setData(data)
  else map.addSource(sourceId, { type: 'geojson', data })
}

const PLACE_CATEGORIES = [
  { value: '', label: 'Categoria livre' },
  { value: 'posto de combustível', label: 'Postos de combustível' },
  { value: 'terminal logístico', label: 'Terminais logísticos' },
  { value: 'oficina mecânica', label: 'Oficinas' },
  { value: 'hospital', label: 'Hospitais' },
  { value: 'base operacional', label: 'Bases operacionais' },
  { value: 'cliente industrial', label: 'Clientes industriais' },
]

function geofenceTypeForPlace(place: MapPlaceResult) {
  const value = `${place.category || ''} ${place.title || ''}`.toLowerCase()
  if (value.includes('combust') || value.includes('gas') || value.includes('fuel')) return 'FUEL_STATION'
  if (value.includes('hospital') || value.includes('clínica') || value.includes('clinica')) return 'CHECKPOINT'
  if (value.includes('oficina') || value.includes('garage') || value.includes('mec')) return 'CHECKPOINT'
  if (value.includes('terminal') || value.includes('porto') || value.includes('log')) return 'TERMINAL'
  if (value.includes('cliente') || value.includes('customer')) return 'CLIENT'
  return 'CHECKPOINT'
}

export function RealFleetMap({ positions, geofences = [], replay = null, onMarkerClick }: { positions: GPSPosition[]; geofences?: GeofenceRecord[]; replay?: GPSReplayData | null; onMarkerClick?: (position: GPSPosition) => void }) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const markersRef = useRef<Marker[]>([])
  const placeMarkerRef = useRef<Marker | null>(null)
  const [mapReady, setMapReady] = useState(0)
  const [status, setStatus] = useState<MapStatus | null>(null)
  const [provider, setProvider] = useState<ResolvedMapProvider | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [placeQuery, setPlaceQuery] = useState('')
  const [placeCategory, setPlaceCategory] = useState('')
  const [placeResults, setPlaceResults] = useState<MapPlaceResult[]>([])
  const [placeBusy, setPlaceBusy] = useState(false)
  const [placeError, setPlaceError] = useState<string | null>(null)
  const [placeMessage, setPlaceMessage] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function boot() {
      try {
        const mapStatus = await api.mapStatus() as unknown as MapStatus
        if (cancelled) return
        setStatus(mapStatus)
        const selected = resolveMapProvider(mapStatus)
        setProvider(selected)
        if (selected.kind === 'GOOGLE_ONLINE') {
          setMapReady(Date.now())
          return
        }
        const style = styleForProvider(selected)
        if (!containerRef.current || cancelled) return

        const token = tokenStore.access()
        const map = new maplibregl.Map({
          container: containerRef.current,
          style,
          center: mapStatus.angola_view?.center ?? [17.8739, -11.2027],
          zoom: 5,
          minZoom: mapStatus.angola_view?.min_zoom ?? 4,
          maxZoom: mapStatus.angola_view?.max_zoom ?? 16,
          maxBounds: mapStatus.angola_view?.bounds,
          transformRequest: (url) => {
            if (url.includes('/api/v1/') && token) return { url, headers: { Authorization: `Bearer ${token}` } }
            return { url }
          },
        })
        mapRef.current = map
        map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right')
        map.addControl(new maplibregl.GeolocateControl({ positionOptions: { enableHighAccuracy: true }, trackUserLocation: false }), 'top-right')
        map.on('load', () => setMapReady(Date.now()))
        map.on('error', (event) => {
          const fallback = mapStatus.mode === 'auto' && selected.kind === 'ONLINE_RASTER' ? offlineFallbackProvider(mapStatus) : null
          if (!fallback) {
            setError(event.error?.message || 'Falha do provider cartográfico real.')
            return
          }
          try {
            setProvider(fallback)
            map.setStyle(styleForProvider(fallback))
            map.once('styledata', () => setMapReady(Date.now()))
          } catch (reason) {
            setError(reason instanceof Error ? reason.message : 'Mapa offline indisponível.')
          }
        })
      } catch (reason) {
        if (!cancelled) setError(reason instanceof Error ? reason.message : 'Mapa GIS indisponível.')
      }
    }
    void boot()
    return () => {
      cancelled = true
      placeMarkerRef.current?.remove()
      placeMarkerRef.current = null
      markersRef.current.forEach((marker) => marker.remove())
      markersRef.current = []
      mapRef.current?.remove()
      mapRef.current = null
    }
  }, [])

  const searchPlaces = useCallback(async (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault()
    const query = placeQuery.trim()
    if (!query) return
    setPlaceBusy(true)
    setPlaceError(null)
    setPlaceMessage(null)
    try {
      const params = new URLSearchParams({
        query,
        language: 'pt',
        country: 'ao',
        limit: '8',
      })
      if (placeCategory) params.set('category', placeCategory)
      const map = mapRef.current
      if (map) {
        const center = map.getCenter()
        params.set('latitude', String(center.lat))
        params.set('longitude', String(center.lng))
        params.set('zoom', String(Math.round(map.getZoom())))
      }
      const rows = await api.searchMapPlaces(params)
      setPlaceResults(rows)
      if (!rows.length) setPlaceMessage('Nenhum local encontrado para esta pesquisa.')
    } catch (reason) {
      setPlaceResults([])
      setPlaceError(reason instanceof ApiError ? reason.message : 'Não foi possível pesquisar locais.')
    } finally {
      setPlaceBusy(false)
    }
  }, [placeCategory, placeQuery])

  const showPlace = useCallback((place: MapPlaceResult) => {
    const map = mapRef.current
    if (!map) {
      setPlaceError('Para mostrar o ponto no mapa, use o provider MapLibre online/offline nesta vista.')
      return
    }
    const center: [number, number] = [place.longitude, place.latitude]
    map.flyTo({ center, zoom: Math.max(map.getZoom(), 12.5), essential: true })
    placeMarkerRef.current?.remove()
    const element = document.createElement('button')
    element.type = 'button'
    element.className = 'map-place-marker'
    element.title = place.title
    element.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 0 5.5z"/></svg>'
    placeMarkerRef.current = new maplibregl.Marker({ element }).setLngLat(center).addTo(map)
    setPlaceError(null)
    setPlaceMessage(`${place.title} marcado no mapa.`)
  }, [])

  const savePlace = useCallback(async (place: MapPlaceResult) => {
    setPlaceBusy(true)
    setPlaceError(null)
    setPlaceMessage(null)
    try {
      await api.createGeofence({
        name: place.title,
        geofence_type: geofenceTypeForPlace(place),
        shape_type: 'point',
        geometry: {
          center: [place.longitude, place.latitude],
          source: place.source,
          external_id: place.external_id,
          address: place.address,
          category: place.category,
          retrieved_at: place.retrieved_at,
        },
        radius_meters: 120,
        alert_on_enter: true,
        alert_on_exit: false,
        status: 'active',
      })
      setPlaceMessage(`${place.title} guardado como ponto operacional.`)
    } catch (reason) {
      setPlaceError(reason instanceof ApiError ? reason.message : 'Não foi possível guardar o ponto operacional.')
    } finally {
      setPlaceBusy(false)
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    markersRef.current.forEach((marker) => marker.remove())
    markersRef.current = positions
      .filter((position) => Number.isFinite(position.longitude) && Number.isFinite(position.latitude))
      .map((position) => {
        const element = document.createElement('button')
        element.className = `gps-marker real ${position.vehicle_state}`
        element.type = 'button'
        element.title = `${position.truck.plate} · ${Math.round(position.speed_kmh)} km/h · ${position.vehicle_state}`
        element.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 17h4v2h-4z"/><path d="M4 6h12l4 5v6h-2a3 3 0 0 1-6 0H9a3 3 0 0 1-6 0H1V9a3 3 0 0 1 3-3z"/></svg><i></i>'
        element.addEventListener('click', () => onMarkerClick?.(position))
        return new maplibregl.Marker({ element }).setLngLat([position.longitude, position.latitude]).addTo(map)
      })
  }, [positions, onMarkerClick, mapReady])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapReady) return
    const features = geofences.map(geofenceFeature).filter(Boolean) as NonNullable<ReturnType<typeof geofenceFeature>>[]
    setMapData(map, 'fnl-geofences', { type: 'FeatureCollection', features } as maplibregl.GeoJSONSourceSpecification['data'])
    if (!map.getLayer('fnl-geofences-fill')) {
      map.addLayer({ id: 'fnl-geofences-fill', type: 'fill', source: 'fnl-geofences', paint: { 'fill-color': '#1d9bf0', 'fill-opacity': 0.12 } })
      map.addLayer({ id: 'fnl-geofences-line', type: 'line', source: 'fnl-geofences', paint: { 'line-color': '#38bdf8', 'line-width': 2, 'line-dasharray': [2, 1] } })
    }

    const coordinates = replay?.positions?.map((point) => [point.longitude, point.latitude]) ?? []
    setMapData(map, 'fnl-replay', {
      type: 'FeatureCollection',
      features: coordinates.length >= 2 ? [{ type: 'Feature', geometry: { type: 'LineString', coordinates }, properties: { count: coordinates.length } }] : [],
    } as maplibregl.GeoJSONSourceSpecification['data'])
    if (!map.getLayer('fnl-replay-line')) {
      map.addLayer({ id: 'fnl-replay-line', type: 'line', source: 'fnl-replay', paint: { 'line-color': '#f59e0b', 'line-width': 4, 'line-opacity': 0.78 } })
    }

    return () => {
      removeLayers(map, ['fnl-geofences-fill', 'fnl-geofences-line', 'fnl-replay-line'])
      removeSources(map, ['fnl-geofences', 'fnl-replay'])
    }
  }, [geofences, replay, mapReady])

  return (
    <div className="real-map-shell">
      {provider?.kind === 'GOOGLE_ONLINE'
        ? <GoogleMapsOnlineProvider status={status} positions={positions} onMarkerClick={onMarkerClick} />
        : <div ref={containerRef} className="real-map-container" />}
      {provider?.kind !== 'GOOGLE_ONLINE' && (
        <form className="map-place-search" onSubmit={searchPlaces}>
          <div className="map-place-search-row">
            <label>
              <span>Pesquisa auxiliar SerpApi</span>
              <input value={placeQuery} onChange={(event) => setPlaceQuery(event.target.value)} placeholder="Ex.: Sonangol, porto, oficina, hospital..." />
            </label>
            <label>
              <span>Categoria</span>
              <select value={placeCategory} onChange={(event) => setPlaceCategory(event.target.value)}>
                {PLACE_CATEGORIES.map((item) => <option key={item.value || 'all'} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <button type="submit" disabled={placeBusy || !placeQuery.trim()}>{placeBusy ? 'A pesquisar...' : 'Pesquisar'}</button>
          </div>
          {(placeError || placeMessage || placeResults.length > 0) && (
            <div className="map-place-results">
              {placeError && <p className="map-place-error">{placeError}</p>}
              {placeMessage && <p className="map-place-message">{placeMessage}</p>}
              {placeResults.map((place) => (
                <article key={place.external_id}>
                  <MapPin />
                  <div>
                    <strong>{place.title}</strong>
                    <span>{place.category || 'local'}{place.address ? ` · ${place.address}` : ''}</span>
                    <small>{place.latitude.toFixed(5)}, {place.longitude.toFixed(5)} · {place.source}</small>
                  </div>
                  <button type="button" onClick={() => showPlace(place)}>Mostrar</button>
                  <button type="button" onClick={() => void savePlace(place)} disabled={placeBusy}>Guardar</button>
                </article>
              ))}
            </div>
          )}
        </form>
      )}
      {error && (
        <div className="map-unavailable-panel">
          <AlertTriangle />
          <strong>Mapa GIS real indisponível</strong>
          <span>{error}</span>
          <small>Modo: {status?.mode || 'n/d'} · Provider: {provider?.label || 'MAP_UNAVAILABLE'}</small>
          <p>Importe um pacote PMTiles/MBTiles real ou configure provider online. O sistema não desenha mapa fictício.</p>
        </div>
      )}
      {!error && !mapReady && (
        <div className="map-loading-panel">
          <Satellite className="spin" />
          <span>A carregar provider GIS real…</span>
        </div>
      )}
      <div className="map-legend real">
        <span><i /> {positions.length} posição(ões) GPS</span>
        <span><i /> {provider?.label || 'a resolver provider'}</span>
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
      const next = await api.mapStatus() as unknown as MapStatus
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
      const next = await api.setMapMode(nextMode) as unknown as MapStatus
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

  const active = status?.active_package as MapPackage | undefined

  return (
    <section className="offline-map-manager">
      <header>
        <div><Map /><p><strong>Gestor de mapas offline</strong><small>{status?.storage.map_dir || 'A carregar localização...'}</small></p></div>
        <button className="module-secondary-button" disabled={busy} onClick={() => void load()}><RefreshCw className={busy ? 'spin' : ''} /> Atualizar</button>
      </header>
      {error && <p className="map-manager-error">{error}</p>}
      <div className="map-manager-controls">
        <label><span>Modo</span><select value={mode} onChange={(event) => void changeMode(event.target.value as MapMode)}><option value="auto">Auto: online com fallback offline</option><option value="online">Online MapLibre</option><option value="offline">Offline local</option></select></label>
        <span>Espaço livre: <strong>{formatBytes(status?.storage.free_bytes)}</strong></span>
        <span>Ativo: <strong>{active?.original_name || 'sem pacote offline'}</strong></span>
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
        )) : <p className="empty-map-packages">Sem pacotes offline importados. O sistema não mostra mapa fictício: use online MapLibre ou importe PMTiles/MBTiles real.</p>}
      </div>
    </section>
  )
}
