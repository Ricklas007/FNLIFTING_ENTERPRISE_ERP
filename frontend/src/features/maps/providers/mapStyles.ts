import type { StyleSpecification } from 'maplibre-gl'

import { apiUrl } from '@/services/api'

import type { MapPackage } from '../types'

const RASTER_TILE_FORMATS = new Set(['png', 'jpg', 'jpeg', 'webp', 'unknown', undefined, null])
const VECTOR_TILE_FORMATS = new Set(['pbf', 'mvt'])

export function isRasterMbtiles(pkg: MapPackage) {
  return pkg.provider === 'OFFLINE_MBTILES' && RASTER_TILE_FORMATS.has(pkg.tile_format)
}

export function isVectorTilePackage(pkg: MapPackage) {
  return pkg.provider === 'OFFLINE_PMTILES' || (pkg.provider === 'OFFLINE_MBTILES' && VECTOR_TILE_FORMATS.has(pkg.tile_format || ''))
}

export function onlineRasterStyle(): StyleSpecification {
  const styleUrl = import.meta.env.VITE_MAP_ONLINE_STYLE_URL as string | undefined
  if (styleUrl) {
    return {
      version: 8,
      sources: {
        online: {
          type: 'raster',
          tiles: [styleUrl],
          tileSize: 256,
          attribution: import.meta.env.VITE_MAP_ONLINE_ATTRIBUTION || 'Fornecedor cartográfico online configurado',
        },
      },
      layers: [{ id: 'online-raster', type: 'raster', source: 'online' }],
    }
  }
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
    layers: [{ id: 'osm-raster', type: 'raster', source: 'osm' }],
  }
}

export function offlineRasterStyle(pkg: MapPackage): StyleSpecification {
  return {
    version: 8,
    sources: {
      offline: {
        type: 'raster',
        tiles: [apiUrl(`/maps/packages/${pkg.id}/tiles/{z}/{x}/{y}.png`)],
        tileSize: 256,
        attribution: pkg.license || pkg.source || 'Pacote MBTiles offline importado',
      },
    },
    layers: [{ id: 'offline-raster', type: 'raster', source: 'offline' }],
  }
}

function openMapTilesVectorLayers(source: string) {
  return [
    { id: `${source}-background`, type: 'background', paint: { 'background-color': '#020817' } },
    { id: `${source}-water`, type: 'fill', source, 'source-layer': 'water', paint: { 'fill-color': '#061a35' } },
    { id: `${source}-landcover`, type: 'fill', source, 'source-layer': 'landcover', paint: { 'fill-color': '#06223a', 'fill-opacity': 0.34 } },
    { id: `${source}-park`, type: 'fill', source, 'source-layer': 'park', paint: { 'fill-color': '#06351f', 'fill-opacity': 0.34 } },
    { id: `${source}-boundary`, type: 'line', source, 'source-layer': 'boundary', paint: { 'line-color': '#2b6da8', 'line-width': 1, 'line-opacity': 0.45 } },
    { id: `${source}-road-minor`, type: 'line', source, 'source-layer': 'transportation', filter: ['in', ['get', 'class'], ['literal', ['minor', 'service', 'track']]], paint: { 'line-color': '#27608f', 'line-width': ['interpolate', ['linear'], ['zoom'], 5, 0.35, 12, 1.4], 'line-opacity': 0.62 } },
    { id: `${source}-road-major`, type: 'line', source, 'source-layer': 'transportation', filter: ['in', ['get', 'class'], ['literal', ['primary', 'secondary', 'tertiary', 'trunk', 'motorway']]], paint: { 'line-color': '#149dff', 'line-width': ['interpolate', ['linear'], ['zoom'], 5, 0.8, 12, 3.2], 'line-opacity': 0.86 } },
  ] as StyleSpecification['layers']
}

export function offlineVectorStyle(pkg: MapPackage): StyleSpecification {
  const sourceName = 'offline-vector'
  const isPmtiles = pkg.provider === 'OFFLINE_PMTILES'
  return {
    version: 8,
    sources: {
      [sourceName]: isPmtiles
        ? {
            type: 'vector',
            url: `pmtiles://${apiUrl(`/maps/packages/${pkg.id}/pmtiles`)}`,
            attribution: pkg.license || pkg.source || 'Pacote PMTiles offline importado',
          }
        : {
            type: 'vector',
            tiles: [apiUrl(`/maps/packages/${pkg.id}/tiles/{z}/{x}/{y}.pbf`)],
            attribution: pkg.license || pkg.source || 'Pacote MBTiles vectorial importado',
          },
    },
    layers: openMapTilesVectorLayers(sourceName),
  }
}

export function styleForOfflinePackage(pkg: MapPackage): StyleSpecification {
  if (isRasterMbtiles(pkg)) return offlineRasterStyle(pkg)
  if (isVectorTilePackage(pkg)) return offlineVectorStyle(pkg)
  throw new Error(`Formato offline não suportado para renderização: ${pkg.tile_format || pkg.provider}`)
}
