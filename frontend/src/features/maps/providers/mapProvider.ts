import type { MapStatus, ResolvedMapProvider } from '../types'

export function googleMapsConfigured() {
  return Boolean(import.meta.env.VITE_MAP_GOOGLE_API_KEY)
}

export function resolveMapProvider(status: MapStatus): ResolvedMapProvider {
  const activePackage = status.active_package || undefined

  if (status.mode === 'offline') {
    if (!activePackage) {
      return {
        kind: 'MAP_UNAVAILABLE',
        label: 'Sem pacote offline ativo',
        mode: status.mode,
        reason: 'Importe e ative um pacote PMTiles/MBTiles real para usar o modo offline.',
      }
    }
    return {
      kind: activePackage.provider,
      label: activePackage.provider,
      mode: status.mode,
      package: activePackage,
    }
  }

  if (status.mode === 'online') {
    const renderer = import.meta.env.VITE_MAP_RENDERER || 'maplibre'
    if (renderer === 'google') {
      return googleMapsConfigured()
        ? { kind: 'GOOGLE_ONLINE', label: 'Google Maps online configurado', mode: status.mode }
        : { kind: 'MAP_UNAVAILABLE', label: 'Google Maps não configurado', mode: status.mode, reason: 'Defina VITE_MAP_GOOGLE_API_KEY e restrições oficiais da chave.' }
    }
    return { kind: 'ONLINE_RASTER', label: 'MapLibre online · OpenStreetMap', mode: status.mode }
  }

  if (navigator.onLine === false && activePackage) {
    return { kind: activePackage.provider, label: `${activePackage.provider} · offline automático`, mode: status.mode, package: activePackage }
  }

  return { kind: 'ONLINE_RASTER', label: 'MapLibre online · OpenStreetMap', mode: status.mode, package: activePackage }
}

export function offlineFallbackProvider(status: MapStatus): ResolvedMapProvider | null {
  const activePackage = status.active_package || undefined
  if (!activePackage) return null
  return { kind: activePackage.provider, label: `${activePackage.provider} · fallback offline`, mode: status.mode, package: activePackage }
}
