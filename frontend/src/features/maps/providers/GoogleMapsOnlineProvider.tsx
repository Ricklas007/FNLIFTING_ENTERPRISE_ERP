import { useEffect, useRef, useState } from 'react'

import type { GPSPosition } from '@/types'

import type { MapStatus } from '../types'

declare global {
  interface Window {
    google?: any
    __fnlGoogleMapsPromise?: Promise<void>
  }
}

function loadGoogleMaps() {
  if (window.google?.maps) return Promise.resolve()
  if (window.__fnlGoogleMapsPromise) return window.__fnlGoogleMapsPromise

  const key = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined
  if (!key) return Promise.reject(new Error('Google Maps API key não configurada.'))

  const mapId = import.meta.env.VITE_GOOGLE_MAP_ID as string | undefined
  const params = new URLSearchParams({ key, v: 'weekly' })
  if (mapId) params.set('map_ids', mapId)
  const script = document.createElement('script')
  script.src = `https://maps.googleapis.com/maps/api/js?${params.toString()}`
  script.async = true
  script.defer = true
  window.__fnlGoogleMapsPromise = new Promise<void>((resolve, reject) => {
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Falha ao carregar Google Maps JavaScript API.'))
  })
  document.head.appendChild(script)
  return window.__fnlGoogleMapsPromise
}

export function GoogleMapsOnlineProvider({ status, positions, onMarkerClick }: { status: MapStatus | null; positions: GPSPosition[]; onMarkerClick?: (position: GPSPosition) => void }) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<any>(null)
  const markersRef = useRef<any[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function boot() {
      try {
        await loadGoogleMaps()
        if (cancelled || !containerRef.current || !window.google?.maps) return
        mapRef.current = new window.google.maps.Map(containerRef.current, {
          center: { lat: status?.angola_view?.center?.[1] ?? -11.2027, lng: status?.angola_view?.center?.[0] ?? 17.8739 },
          zoom: 6,
          mapId: import.meta.env.VITE_GOOGLE_MAP_ID || undefined,
          fullscreenControl: false,
          streetViewControl: false,
          mapTypeControl: false,
        })
      } catch (reason) {
        if (!cancelled) setError(reason instanceof Error ? reason.message : 'Google Maps indisponível.')
      }
    }
    void boot()
    return () => {
      cancelled = true
      markersRef.current.forEach((marker) => marker.setMap(null))
      markersRef.current = []
      mapRef.current = null
    }
  }, [status])

  useEffect(() => {
    if (!mapRef.current || !window.google?.maps) return
    markersRef.current.forEach((marker) => marker.setMap(null))
    markersRef.current = positions.map((position) => {
      const marker = new window.google.maps.Marker({
        map: mapRef.current,
        position: { lat: position.latitude, lng: position.longitude },
        title: `${position.truck.plate} · ${Math.round(position.speed_kmh)} km/h`,
      })
      marker.addListener('click', () => onMarkerClick?.(position))
      return marker
    })
    if (positions.length) {
      const bounds = new window.google.maps.LatLngBounds()
      positions.forEach((position) => bounds.extend({ lat: position.latitude, lng: position.longitude }))
      mapRef.current.fitBounds(bounds)
    }
  }, [positions, onMarkerClick])

  return (
    <div className="google-map-provider">
      <div ref={containerRef} className="real-map-container" />
      {error && <div className="map-unavailable-panel"><strong>Google Maps não disponível</strong><span>{error}</span><p>Use MapLibre online/offline ou configure a chave oficial com restrições.</p></div>}
    </div>
  )
}
