import type { LucideIcon } from 'lucide-react'

export function money(value: number) {
  return new Intl.NumberFormat('pt-AO', { style: 'currency', currency: 'AOA', maximumFractionDigits: 0 }).format(value)
}

export function dateLabel(value?: string) {
  return value ? new Date(value.includes('T') ? value : `${value}T00:00:00`).toLocaleDateString('pt-AO') : '—'
}

export function MetricCard({ label, value, icon: Icon }: { label: string; value: string | number; icon: LucideIcon }) {
  return <article className="phase-metric-card"><span><Icon /></span><small>{label}</small><strong>{value}</strong></article>
}
