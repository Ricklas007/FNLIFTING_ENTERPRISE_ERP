export type MapMode = 'auto' | 'offline' | 'online'

export type MapRenderer = 'maplibre' | 'google'

export type MapProviderKind =
  | 'OFFLINE_PMTILES'
  | 'OFFLINE_MBTILES'
  | 'ONLINE_VECTOR'
  | 'ONLINE_RASTER'
  | 'GOOGLE_ONLINE'
  | 'MAP_UNAVAILABLE'

export interface MapPackage {
  id: string
  provider: 'OFFLINE_PMTILES' | 'OFFLINE_MBTILES'
  original_name: string
  stored_name?: string
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
  metadata?: Record<string, unknown>
}

export interface MapStatus {
  mode: MapMode
  providers?: Record<string, { available: boolean; reason?: string; style?: string; attribution?: string }>
  active_package?: MapPackage | null
  packages: MapPackage[]
  storage: {
    map_dir: string
    cache_dir: string
    free_bytes?: number
    total_bytes?: number
  }
  angola_view?: {
    center?: [number, number]
    bounds?: [number, number, number, number]
    min_zoom?: number
    max_zoom?: number
  }
}

export interface ResolvedMapProvider {
  kind: MapProviderKind
  label: string
  mode: MapMode
  package?: MapPackage
  reason?: string
}
