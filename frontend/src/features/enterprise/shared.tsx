import type { LucideIcon } from 'lucide-react'

export function MetricCard({ label, value, icon: Icon }: { label: string; value: string | number; icon: LucideIcon }) {
  return <article className="phase-metric-card"><span><Icon /></span><small>{label}</small><strong>{value}</strong></article>
}
