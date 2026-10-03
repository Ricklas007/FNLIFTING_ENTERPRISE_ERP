export function money(value: number) {
  return new Intl.NumberFormat('pt-AO', { style: 'currency', currency: 'AOA', maximumFractionDigits: 0 }).format(value)
}

export function dateLabel(value?: string) {
  return value ? new Date(value.includes('T') ? value : `${value}T00:00:00`).toLocaleDateString('pt-AO') : '—'
}
