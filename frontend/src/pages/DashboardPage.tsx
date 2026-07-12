import { useEffect, useMemo, useState } from 'react'
import {
  Activity, ArrowRight, BadgeCheck, BellRing, Boxes, CalendarDays, CheckCircle2,
  ChevronRight, CircleAlert, ClockAlert, FileClock, Landmark, MoreHorizontal,
  PackageCheck, RefreshCw, ScanSearch, TrendingUp, Truck, Users, WalletCards,
} from 'lucide-react'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip,
  XAxis, YAxis,
} from 'recharts'
import { api, ApiError } from '@/services/api'
import type { DashboardData, Metric } from '@/types'
import { cn } from '@/lib/utils'

const metricIcons: Record<string, typeof Users> = {
  users: Users, 'file-clock': FileClock, 'scan-search': ScanSearch, 'badge-check': BadgeCheck,
  truck: Truck, 'trending-up': TrendingUp, 'wallet-cards': WalletCards, landmark: Landmark,
  'package-check': PackageCheck, 'clock-alert': ClockAlert, 'clipboard-list': FileClock,
}

function MetricCard({ metric, index }: { metric: Metric; index: number }) {
  const Icon = metricIcons[metric.icon] ?? Activity
  return (
    <article className="metric-card" style={{ '--delay': `${index * 60}ms` } as React.CSSProperties}>
      <div className={cn('metric-icon', metric.trend === 'warning' && 'warning')}><Icon size={20} /></div>
      <button className="metric-more" aria-label="Mais opções"><MoreHorizontal size={17} /></button>
      <p>{metric.label}</p>
      <strong>{metric.display_value}</strong>
      <div className={cn('metric-change', metric.trend)}>
        {metric.trend === 'up' ? <TrendingUp size={13} /> : metric.trend === 'warning' ? <CircleAlert size={13} /> : <CheckCircle2 size={13} />}
        {metric.change}
      </div>
    </article>
  )
}

const tooltipStyle = {
  background: 'rgba(4, 13, 31, .96)', border: '1px solid rgba(90, 150, 230, .2)',
  borderRadius: 12, boxShadow: '0 16px 38px rgba(0,0,0,.35)', fontSize: 12,
}

export function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  async function load() {
    setRefreshing(true); setError(null)
    try { setData(await api.dashboard()) }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Não foi possível carregar o dashboard.') }
    finally { setRefreshing(false) }
  }

  useEffect(() => { void load() }, [])
  const formattedDate = useMemo(() => new Intl.DateTimeFormat('pt-AO', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' }).format(new Date()), [])

  return (
    <>
      <section className="dashboard-head">
        <div>
          <div className="dashboard-breadcrumb"><span>FNLIFTING ERP</span><ChevronRight size={12} />Dashboard</div>
          <h1>{data?.greeting ?? 'Visão operacional'}</h1>
          <p>{data?.scope === 'client' ? 'Acompanhe os serviços e documentos da sua empresa.' : 'Aqui está o pulso das operações da FNLIFTING neste momento.'}</p>
        </div>
        <div className="dashboard-head-actions">
          <span className="date-chip"><CalendarDays size={16} />{formattedDate}</span>
          <button className="refresh-button" onClick={load} disabled={refreshing}><RefreshCw className={refreshing ? 'animate-spin' : ''} size={16} /> Atualizar</button>
        </div>
      </section>

      {error && <div className="dashboard-error"><CircleAlert /><div><strong>Falha ao carregar dados</strong><p>{error}</p></div><button onClick={load}>Tentar novamente</button></div>}

      {!data && !error ? (
        <div className="dashboard-skeleton"><div /><div /><div /><div /></div>
      ) : data && (
        <>
          <section className={cn('metrics-grid', data.scope === 'client' && 'client-metrics')}>
            {data.metrics.map((metric, index) => <MetricCard key={metric.key} metric={metric} index={index} />)}
          </section>

          <section className="dashboard-grid">
            {data.scope === 'enterprise' && (
              <article className="dashboard-panel chart-panel finance-panel">
                <div className="panel-head">
                  <div><span className="panel-kicker">Performance financeira</span><h2>Receita vs. despesa</h2></div>
                  <div className="chart-legend"><span className="revenue-dot" />Receita <span className="expense-dot" />Despesa</div>
                </div>
                <div className="chart-summary"><strong>Kz 27,6M</strong><span><TrendingUp size={13} /> 18,4% no semestre</span></div>
                <ResponsiveContainer width="100%" height={245}>
                  <AreaChart data={data.finance_chart} margin={{ top: 12, right: 8, left: -22, bottom: 0 }}>
                    <defs>
                      <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#1388ff" stopOpacity={0.45}/><stop offset="95%" stopColor="#1388ff" stopOpacity={0}/></linearGradient>
                      <linearGradient id="expenseGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#8a5cf6" stopOpacity={0.22}/><stop offset="95%" stopColor="#8a5cf6" stopOpacity={0}/></linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(118,149,190,.08)" vertical={false} />
                    <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 11 }} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fill: '#536277', fontSize: 10 }} />
                    <Tooltip contentStyle={tooltipStyle} formatter={(value) => [`Kz ${Number(value).toFixed(1)}M`]} />
                    <Area type="monotone" dataKey="revenue" stroke="#178cff" strokeWidth={2.4} fill="url(#revenueGradient)" />
                    <Area type="monotone" dataKey="expense" stroke="#8b66f5" strokeWidth={1.8} fill="url(#expenseGradient)" />
                  </AreaChart>
                </ResponsiveContainer>
              </article>
            )}

            <article className={cn('dashboard-panel chart-panel operations-panel', data.scope === 'client' && 'client-chart')}>
              <div className="panel-head">
                <div><span className="panel-kicker">Qualidade & conformidade</span><h2>{data.scope === 'client' ? 'Inspeções da empresa' : 'Inspeções realizadas'}</h2></div>
                <button className="panel-action">Ver relatório <ArrowRight size={14} /></button>
              </div>
              <ResponsiveContainer width="100%" height={data.scope === 'client' ? 295 : 265}>
                <BarChart data={data.operations_chart} margin={{ top: 25, right: 4, left: -30, bottom: 0 }}>
                  <CartesianGrid stroke="rgba(118,149,190,.07)" vertical={false} />
                  <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 11 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#536277', fontSize: 10 }} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'rgba(20,130,255,.06)' }} />
                  <Bar dataKey="inspections" fill="#1587ff" radius={[5,5,0,0]} maxBarSize={26} />
                </BarChart>
              </ResponsiveContainer>
            </article>

            <article className="dashboard-panel alerts-panel">
              <div className="panel-head">
                <div><span className="panel-kicker">Monitorização</span><h2>Alertas importantes</h2></div>
                <span className="panel-count">{data.alerts.length}</span>
              </div>
              <div className="alert-list">
                {data.alerts.map(alert => (
                  <button className="alert-row" key={alert.id}>
                    <span className={cn('alert-icon', alert.level)}>{alert.level === 'critical' ? <CircleAlert /> : alert.level === 'warning' ? <ClockAlert /> : <BellRing />}</span>
                    <span><strong>{alert.title}</strong><small>{alert.detail}</small></span><time>{alert.time}</time><ChevronRight size={15} />
                  </button>
                ))}
              </div>
              <button className="panel-footer-button">Ver todos os alertas <ArrowRight size={14} /></button>
            </article>

            <article className="dashboard-panel activity-panel">
              <div className="panel-head">
                <div><span className="panel-kicker">Em tempo real</span><h2>Atividade recente</h2></div>
                <span className="live-chip"><span /> AO VIVO</span>
              </div>
              <div className="activity-timeline">
                {data.activities.map((activity, index) => (
                  <div className="activity-row" key={activity.id}>
                    <span className="activity-node">{activity.type === 'certificate' ? <BadgeCheck /> : activity.type === 'trip' ? <Truck /> : activity.type === 'inspection' ? <ScanSearch /> : <FileClock />}</span>
                    {index < data.activities.length - 1 && <i />}
                    <div><strong>{activity.title}</strong><p>{activity.detail}</p></div><time>{activity.time}</time>
                  </div>
                ))}
              </div>
            </article>
          </section>
        </>
      )}
    </>
  )
}
