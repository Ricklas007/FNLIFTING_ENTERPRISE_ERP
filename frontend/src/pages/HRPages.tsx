import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import {
  Activity, ArrowRight, Award, BriefcaseBusiness, Building2, CalendarCheck, Check,
  CheckCircle2, ChevronRight, CircleAlert, Clock3, Edit3, FileCheck2, FileClock,
  Filter, Mail, MapPin, Network, Phone, Plus, RefreshCw, Search, Send, Star,
  Trash2, UserCheck, UserRound, Users, X,
} from 'lucide-react'
import { api, ApiError } from '@/services/api'
import { MediaAttachmentPanel } from '@/components/MediaAttachmentPanel'
import { useAuth } from '@/store/useAuth'
import { cn } from '@/lib/utils'
import { hasPermission } from '@/lib/permissions'
import type {
  AppView, DailyReport, Department, Employee, HRSummary, PerformanceReview,
} from '@/types'

export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return (
    <section className="module-head">
      <div><div className="dashboard-breadcrumb"><span>FNLIFTING ERP</span><ChevronRight size={12} />{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>
      {action && <div className="module-head-action">{action}</div>}
    </section>
  )
}

export function Modal({ title, subtitle, onClose, children, wide = false }: { title: string; subtitle: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  return (
    <div className="module-modal-layer" role="dialog" aria-modal="true" aria-label={title}>
      <button className="module-modal-backdrop" onClick={onClose} aria-label="Fechar janela" />
      <section className={cn('module-modal', wide && 'wide')}>
        <header><div><span>FNLIFTING · Recursos Humanos</span><h2>{title}</h2><p>{subtitle}</p></div><button type="button" onClick={onClose} aria-label="Fechar formulário"><X /></button></header>
        <div className="module-modal-body">{children}</div>
      </section>
    </div>
  )
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="module-error"><CircleAlert /><span>{message}</span>{onRetry && <button onClick={onRetry}>Tentar novamente</button>}</div>
}

export function LoadingRows() {
  return <div className="module-loading"><span className="button-spinner" />A carregar dados locais...</div>
}

export function SubmitButton({ busy, children }: { busy: boolean; children: ReactNode }) {
  return <button className="module-primary-button" type="submit" disabled={busy}>{busy ? <span className="button-spinner" /> : children}</button>
}

export function HRPage({ onNavigate }: { onNavigate: (view: AppView) => void }) {
  const [summary, setSummary] = useState<HRSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  async function load() {
    setError(null)
    try { setSummary(await api.hrSummary()) } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Falha ao carregar o painel de RH.') }
  }
  useEffect(() => { void load() }, [])
  const cards = summary ? [
    { label: 'Trabalhadores ativos', value: summary.active_employees, detail: `${summary.employees_on_leave} em férias/ausência`, icon: Users, tone: 'blue' },
    { label: 'Departamentos', value: summary.departments, detail: 'Estrutura organizacional', icon: Network, tone: 'violet' },
    { label: 'Relatórios pendentes', value: summary.pending_reports, detail: `${summary.reports_this_month} recebidos este mês`, icon: FileClock, tone: 'amber' },
    { label: 'Desempenho médio', value: `${summary.average_performance.toFixed(1)}%`, detail: 'Avaliações publicadas', icon: Award, tone: 'green' },
  ] : []
  return (
    <>
      <PageHeader eyebrow="Pessoas · Recursos Humanos" title="Centro de Recursos Humanos" description="Visão consolidada da equipa, produtividade e rotinas diárias." action={<button className="module-secondary-button" onClick={load}><RefreshCw size={15} /> Atualizar</button>} />
      {error && <ErrorBanner message={error} onRetry={load} />}
      {!summary && !error ? <LoadingRows /> : summary && <>
        <section className="hr-metrics-grid">{cards.map(({ label, value, detail, icon: Icon, tone }) => <article className="hr-metric" key={label}><span className={tone}><Icon /></span><div><p>{label}</p><strong>{value}</strong><small>{detail}</small></div></article>)}</section>
        <section className="hr-dashboard-grid">
          <article className="module-panel hr-distribution"><div className="module-panel-head"><div><span>Estrutura organizacional</span><h2>Trabalhadores por departamento</h2></div><Building2 /></div><div className="distribution-list">{summary.department_distribution.map(item => { const max = Math.max(...summary.department_distribution.map(row => row.value), 1); return <div key={item.name}><p><span>{item.name}</span><strong>{item.value}</strong></p><i><b style={{ width: `${Math.max((item.value / max) * 100, 4)}%` }} /></i></div> })}</div></article>
          <article className="module-panel top-performers"><div className="module-panel-head"><div><span>Ranking interno</span><h2>Destaques do mês</h2></div><Award /></div><div className="performer-list">{summary.top_performers.map((person, index) => <div key={person.name}><span className="rank">{index + 1}</span><span className="person-avatar">{person.name.split(' ').map(part => part[0]).slice(0,2).join('')}</span><p><strong>{person.name}</strong><small>{person.job_title}</small></p><em>{person.score.toFixed(1)}%</em></div>)}</div></article>
          <article className="module-panel hr-quick-actions"><div className="module-panel-head"><div><span>Atalhos operacionais</span><h2>Gestão de pessoas</h2></div></div><div className="quick-action-grid">
            <button onClick={() => onNavigate('employees')}><span><UserRound /></span><div><strong>Trabalhadores</strong><small>Cadastro e contratos</small></div><ArrowRight /></button>
            <button onClick={() => onNavigate('daily-reports')}><span><FileCheck2 /></span><div><strong>Relatórios diários</strong><small>Submissão e revisão</small></div><ArrowRight /></button>
            <button onClick={() => onNavigate('performance')}><span><Activity /></span><div><strong>Desempenho</strong><small>Scores e ranking</small></div><ArrowRight /></button>
            <button onClick={() => onNavigate('departments')}><span><Network /></span><div><strong>Departamentos</strong><small>Estrutura organizacional</small></div><ArrowRight /></button>
          </div></article>
        </section>
      </>}
    </>
  )
}

function EmployeeForm({ departments, employee, onSaved, onClose }: { departments: Department[]; employee?: Employee; onSaved: () => void; onClose: () => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(null)
    const data = Object.fromEntries(new FormData(event.currentTarget)) as Record<string,string>
    const payload: Record<string, unknown> = {
      department_id: data.department_id, employee_no: data.employee_no, full_name: data.full_name,
      job_title: data.job_title, birth_date: data.birth_date || null, bi: data.bi || null, nif: data.nif || null,
      phone: data.phone || null, email: data.email || null, address: data.address || null,
      admission_date: data.admission_date, contract_type: data.contract_type, salary: data.salary || null,
      contract_status: data.contract_status, status: data.status,
    }
    try { employee ? await api.updateEmployee(employee.id, payload) : await api.createEmployee(payload); onSaved(); onClose() }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Não foi possível guardar o trabalhador.') }
    finally { setBusy(false) }
  }
  return <form className="module-form" onSubmit={submit}>{error && <ErrorBanner message={error} />}
    <div className="form-section-title"><UserRound /> Identificação profissional</div><div className="module-form-grid three">
      <label><span>Número interno</span><input name="employee_no" defaultValue={employee?.employee_no} required placeholder="FNL-0011" /></label>
      <label className="span-two"><span>Nome completo</span><input name="full_name" defaultValue={employee?.full_name} required placeholder="Nome completo" /></label>
      <label><span>Departamento</span><select name="department_id" defaultValue={employee?.department_id ?? departments[0]?.id} required>{departments.filter(d => d.status === 'active').map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select></label>
      <label><span>Cargo</span><input name="job_title" defaultValue={employee?.job_title} required placeholder="Ex.: Técnico de Inspeção" /></label>
      <label><span>Data de admissão</span><input name="admission_date" type="date" defaultValue={employee?.admission_date ?? new Date().toISOString().slice(0,10)} required /></label>
    </div>
    <div className="form-section-title"><UserCheck /> Dados pessoais e contacto</div><div className="module-form-grid three">
      <label><span>Data de nascimento</span><input name="birth_date" type="date" defaultValue={employee?.birth_date} /></label>
      <label><span>BI</span><input name="bi" defaultValue={employee?.bi} placeholder="000000000LA000" /></label>
      <label><span>NIF</span><input name="nif" defaultValue={employee?.nif} placeholder="Número fiscal" /></label>
      <label><span>Telefone</span><input name="phone" defaultValue={employee?.phone} placeholder="+244 9XX XXX XXX" /></label>
      <label className="span-two"><span>Email</span><input name="email" type="email" defaultValue={employee?.email} placeholder="nome@fnlifting.com" /></label>
      <label className="span-three"><span>Morada</span><input name="address" defaultValue={employee?.address} placeholder="Província, município e bairro" /></label>
    </div>
    <div className="form-section-title"><BriefcaseBusiness /> Contrato e estado</div><div className="module-form-grid three">
      <label><span>Tipo de contrato</span><select name="contract_type" defaultValue={employee?.contract_type ?? 'permanent'}><option value="permanent">Efetivo</option><option value="temporary">Temporário</option><option value="service_provider">Prestador de serviço</option><option value="intern">Estagiário</option><option value="consultant">Consultor</option></select></label>
      <label><span>Salário mensal (Kz)</span><input name="salary" type="number" min="0" step="1000" defaultValue={employee?.salary} /></label>
      <label><span>Estado do contrato</span><select name="contract_status" defaultValue={employee?.contract_status ?? 'active'}><option value="active">Ativo</option><option value="suspended">Suspenso</option><option value="ended">Terminado</option></select></label>
      <label><span>Estado do trabalhador</span><select name="status" defaultValue={employee?.status ?? 'active'}><option value="active">Ativo</option><option value="on_leave">Ausente/Férias</option><option value="inactive">Inativo</option></select></label>
    </div>
    <div className="module-form-actions"><button type="button" className="module-secondary-button" onClick={onClose}>Cancelar</button><SubmitButton busy={busy}><Check size={16} /> Guardar trabalhador</SubmitButton></div>
  </form>
}

export function EmployeesPage() {
  const { user } = useAuth()
  const [records, setRecords] = useState<Employee[]>([]), [departments, setDepartments] = useState<Department[]>([])
  const [search, setSearch] = useState(''), [statusFilter, setStatusFilter] = useState('all')
  const [editing, setEditing] = useState<Employee | null | 'new'>(null), [error, setError] = useState<string | null>(null), [loading, setLoading] = useState(true)
  const canManage = hasPermission(user?.permissions ?? [], 'employees.manage')
  async function load() { setLoading(true); setError(null); try { const [employees, deps] = await Promise.all([api.employees(), api.departments()]); setRecords(employees); setDepartments(deps) } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Falha ao carregar trabalhadores.') } finally { setLoading(false) } }
  useEffect(() => { void load() }, [])
  const filtered = useMemo(() => records.filter(item => { const term = search.toLowerCase(); return (!term || `${item.full_name} ${item.employee_no} ${item.job_title} ${item.department.name}`.toLowerCase().includes(term)) && (statusFilter === 'all' || item.status === statusFilter) }), [records, search, statusFilter])
  async function archive(employee: Employee) { if (!window.confirm(`Arquivar o cadastro de ${employee.full_name}?`)) return; try { await api.deleteEmployee(employee.id); await load() } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Não foi possível arquivar.') } }
  return <><PageHeader eyebrow="Pessoas · Trabalhadores" title="Trabalhadores" description="Cadastro central, contratos, contactos e lotação departamental." action={canManage && <button className="module-primary-button" onClick={() => setEditing('new')}><Plus size={16} /> Novo trabalhador</button>} />
    {error && <ErrorBanner message={error} onRetry={load} />}<section className="module-toolbar"><label><Search /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Pesquisar por nome, número, cargo..." /></label><div><Filter /><select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}><option value="all">Todos os estados</option><option value="active">Ativos</option><option value="on_leave">Ausentes/Férias</option><option value="inactive">Inativos</option></select></div><span>{filtered.length} registos</span></section>
    <section className="module-panel table-panel">{loading ? <LoadingRows /> : <div className="responsive-table"><table><thead><tr><th>Trabalhador</th><th>Departamento</th><th>Contacto</th><th>Contrato</th><th>Estado</th><th /></tr></thead><tbody>{filtered.map(employee => <tr key={employee.id}><td><div className="table-person"><span>{employee.full_name.split(' ').map(part=>part[0]).slice(0,2).join('')}</span><p><strong>{employee.full_name}</strong><small>{employee.employee_no} · {employee.job_title}</small></p></div></td><td><span className="department-chip">{employee.department.name}</span></td><td><div className="contact-cell">{employee.email && <span><Mail />{employee.email}</span>}{employee.phone && <span><Phone />{employee.phone}</span>}</div></td><td><div className="stacked-cell"><strong>{employee.contract_type === 'permanent' ? 'Efetivo' : employee.contract_type === 'temporary' ? 'Temporário' : 'Outro'}</strong><small>Desde {new Date(employee.admission_date).toLocaleDateString('pt-AO')}</small></div></td><td><span className={cn('record-status', employee.status)}>{employee.status === 'active' ? 'Ativo' : employee.status === 'on_leave' ? 'Ausente' : 'Inativo'}</span></td><td>{canManage && <div className="row-actions"><button onClick={() => setEditing(employee)} aria-label={`Editar ${employee.full_name}`}><Edit3 /></button><button className="danger" onClick={() => archive(employee)} aria-label={`Arquivar ${employee.full_name}`}><Trash2 /></button></div>}</td></tr>)}</tbody></table>{!filtered.length && <div className="empty-module"><Users /><strong>Nenhum trabalhador encontrado</strong><p>Altere os filtros ou crie um novo cadastro.</p></div>}</div>}</section>
    {editing && <Modal wide title={editing === 'new' ? 'Novo trabalhador' : 'Editar trabalhador'} subtitle="Os dados ficam disponíveis localmente mesmo sem internet." onClose={() => setEditing(null)}><EmployeeForm departments={departments} employee={editing === 'new' ? undefined : editing} onSaved={load} onClose={() => setEditing(null)} />{editing !== 'new' && <MediaAttachmentPanel entityType="employee" entityId={editing.id} canManage={canManage} title="Fotos, documentos e anexos do trabalhador" />}</Modal>}
  </>
}

function DepartmentForm({ department, onSaved, onClose }: { department?: Department; onSaved: () => void; onClose: () => void }) {
  const [busy,setBusy]=useState(false), [error,setError]=useState<string|null>(null)
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();setBusy(true);setError(null);const data=Object.fromEntries(new FormData(event.currentTarget)) as Record<string,string>;try{department?await api.updateDepartment(department.id,data):await api.createDepartment(data);onSaved();onClose()}catch(reason){setError(reason instanceof ApiError?reason.message:'Não foi possível guardar.')}finally{setBusy(false)}}
  return <form className="module-form" onSubmit={submit}>{error&&<ErrorBanner message={error}/>}<div className="module-form-grid two"><label><span>Código</span><input name="code" required defaultValue={department?.code} placeholder="Ex.: OPE" /></label><label><span>Nome</span><input name="name" required defaultValue={department?.name} placeholder="Nome do departamento" /></label><label className="span-two"><span>Responsável</span><input name="manager_name" defaultValue={department?.manager_name} placeholder="Nome do responsável" /></label><label className="span-two"><span>Descrição</span><textarea name="description" defaultValue={department?.description} rows={4} placeholder="Responsabilidades e âmbito do departamento" /></label><label><span>Estado</span><select name="status" defaultValue={department?.status??'active'}><option value="active">Ativo</option><option value="inactive">Inativo</option></select></label></div><div className="module-form-actions"><button type="button" className="module-secondary-button" onClick={onClose}>Cancelar</button><SubmitButton busy={busy}><Check/> Guardar departamento</SubmitButton></div></form>
}

export function DepartmentsPage(){
  const {user}=useAuth();const [records,setRecords]=useState<Department[]>([]),[editing,setEditing]=useState<Department|null|'new'>(null),[loading,setLoading]=useState(true),[error,setError]=useState<string|null>(null);const canManage=hasPermission(user?.permissions??[],'departments.manage')
  async function load(){setLoading(true);setError(null);try{setRecords(await api.departments())}catch(reason){setError(reason instanceof ApiError?reason.message:'Falha ao carregar departamentos.')}finally{setLoading(false)}}useEffect(()=>{void load()},[])
  async function remove(item:Department){if(!window.confirm(`Eliminar o departamento ${item.name}?`))return;try{await api.deleteDepartment(item.id);await load()}catch(reason){setError(reason instanceof ApiError?reason.message:'Não foi possível eliminar.')}}
  return <><PageHeader eyebrow="Pessoas · Estrutura" title="Departamentos" description="Organize equipas, responsáveis e distribuição dos trabalhadores." action={canManage&&<button className="module-primary-button" onClick={()=>setEditing('new')}><Plus/> Novo departamento</button>}/>{error&&<ErrorBanner message={error} onRetry={load}/>} {loading?<LoadingRows/>:<section className="departments-grid">{records.map(item=><article className="department-card" key={item.id}><header><span><Network/></span><em className={item.status}>{item.status==='active'?'Ativo':'Inativo'}</em></header><small>{item.code}</small><h2>{item.name}</h2><p>{item.description||'Sem descrição.'}</p><div><span><UserCheck/> Responsável</span><strong>{item.manager_name||'Por definir'}</strong></div><footer><span><Users/>{item.employee_count} trabalhador{item.employee_count===1?'':'es'}</span>{canManage&&<div><button onClick={()=>setEditing(item)} aria-label={`Editar ${item.name}`}><Edit3/></button><button onClick={()=>remove(item)} disabled={item.employee_count>0} aria-label={`Eliminar ${item.name}`}><Trash2/></button></div>}</footer></article>)}</section>}{editing&&<Modal title={editing==='new'?'Novo departamento':'Editar departamento'} subtitle="Defina a unidade organizacional e o respetivo responsável." onClose={()=>setEditing(null)}><DepartmentForm department={editing==='new'?undefined:editing} onSaved={load} onClose={()=>setEditing(null)}/></Modal>}</>
}

function DailyReportForm({employees,report,onSaved,onClose}:{employees:Employee[];report?:DailyReport;onSaved:()=>void;onClose:()=>void}){
  const [busy,setBusy]=useState(false),[error,setError]=useState<string|null>(null),[employeeId,setEmployeeId]=useState(report?.employee_id??employees[0]?.id??'');const selected=employees.find(item=>item.id===employeeId)
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();setBusy(true);setError(null);const data=Object.fromEntries(new FormData(event.currentTarget)) as Record<string,string>;try{const payload={summary:data.summary,tasks_performed:data.tasks_performed,start_time:data.start_time||null,end_time:data.end_time||null,work_location:data.work_location||null,difficulties:data.difficulties||null,results_achieved:data.results_achieved||null,observations:data.observations||null,work_status:data.work_status};report?await api.updateDailyReport(report.id,payload):await api.createDailyReport({...payload,report_date:data.report_date,employee_id:employeeId,department_id:selected?.department_id});onSaved();onClose()}catch(reason){setError(reason instanceof ApiError?reason.message:'Não foi possível guardar o relatório.')}finally{setBusy(false)}}
  return <form className="module-form" onSubmit={submit}>{error&&<ErrorBanner message={error}/>}<div className="module-form-grid two"><label><span>Trabalhador</span><select value={employeeId} onChange={e=>setEmployeeId(e.target.value)} required disabled={!!report}>{employees.map(item=><option key={item.id} value={item.id}>{item.full_name} · {item.employee_no}</option>)}</select></label><label><span>Departamento</span><input value={selected?.department.name??report?.department.name??''} disabled /></label><label><span>Data</span><input name="report_date" type="date" defaultValue={report?.report_date??new Date().toISOString().slice(0,10)} required disabled={!!report} /></label><label><span>Estado do trabalho</span><select name="work_status" defaultValue={report?.work_status??'completed'}><option value="completed">Concluído</option><option value="in_progress">Em andamento</option><option value="blocked">Bloqueado</option></select></label><label><span>Início</span><input name="start_time" type="time" defaultValue={report?.start_time?.slice(0,5)??'08:00'} /></label><label><span>Fim</span><input name="end_time" type="time" defaultValue={report?.end_time?.slice(0,5)??'17:00'} /></label><label className="span-two"><span>Local de trabalho</span><input name="work_location" defaultValue={report?.work_location??''} placeholder="Base, cliente ou local da operação" /></label><label className="span-two"><span>Resumo</span><input name="summary" required minLength={5} defaultValue={report?.summary??''} placeholder="Resumo curto do dia" /></label><label className="span-two"><span>Tarefas realizadas</span><textarea name="tasks_performed" rows={5} required minLength={5} defaultValue={report?.tasks_performed??''} placeholder="Descreva as atividades executadas..." /></label><label className="span-two"><span>Resultados alcançados</span><textarea name="results_achieved" rows={3} defaultValue={report?.results_achieved??''} placeholder="Resultados e entregáveis" /></label><label><span>Dificuldades</span><textarea name="difficulties" rows={3} defaultValue={report?.difficulties??''} /></label><label><span>Observações</span><textarea name="observations" rows={3} defaultValue={report?.observations??''} /></label></div><div className="module-form-actions"><button type="button" className="module-secondary-button" onClick={onClose}>Cancelar</button><SubmitButton busy={busy}><Send/> {report?'Guardar e reenviar':'Enviar para revisão'}</SubmitButton></div></form>
}

export function DailyReportsPage(){
  const {user}=useAuth();const [reports,setReports]=useState<DailyReport[]>([]),[employees,setEmployees]=useState<Employee[]>([]),[statusFilter,setStatusFilter]=useState('all'),[formOpen,setFormOpen]=useState(false),[editingReport,setEditingReport]=useState<DailyReport|null>(null),[loading,setLoading]=useState(true),[error,setError]=useState<string|null>(null);const canReview=hasPermission(user?.permissions??[],'daily_reports.review'),canSubmit=hasPermission(user?.permissions??[],'daily_reports.submit'),canViewEmployees=hasPermission(user?.permissions??[],'employees.view')
  const load=useCallback(async()=>{setLoading(true);setError(null);try{const employeePromise=canViewEmployees?api.employees():api.myEmployee().then(item=>[item]);const [items,people]=await Promise.all([api.dailyReports(),employeePromise]);setReports(items);setEmployees(people)}catch(reason){setError(reason instanceof ApiError?reason.message:'Falha ao carregar relatórios.')}finally{setLoading(false)}},[canViewEmployees]);useEffect(()=>{void load()},[load])
  async function review(id:string,action:'approve'|'request_correction'){try{await api.reviewDailyReport(id,action,action==='request_correction'?'Reveja os dados e detalhe melhor os resultados alcançados.':undefined);await load()}catch(reason){setError(reason instanceof ApiError?reason.message:'Não foi possível rever o relatório.')}}
  const filtered=reports.filter(item=>statusFilter==='all'||item.status===statusFilter)
  return <><PageHeader eyebrow="Pessoas · Relatórios diários" title="Relatórios diários" description="Acompanhe o trabalho realizado, bloqueios e resultados de cada equipa." action={canSubmit&&<button className="module-primary-button" onClick={()=>setFormOpen(true)}><Plus/> Novo relatório</button>}/>{error&&<ErrorBanner message={error} onRetry={load}/>}<section className="module-toolbar"><div><Filter/><select value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}><option value="all">Todos os estados</option><option value="pending">Pendentes</option><option value="approved">Aprovados</option><option value="correction_requested">Correção solicitada</option></select></div><span>{filtered.length} relatórios</span></section>{loading?<LoadingRows/>:<section className="reports-list">{filtered.map(report=><article className="report-card" key={report.id}><div className="report-date"><strong>{new Date(`${report.report_date}T00:00:00`).getDate()}</strong><span>{new Date(`${report.report_date}T00:00:00`).toLocaleDateString('pt-AO',{month:'short'})}</span></div><div className="report-main"><header><div><span>{report.employee.full_name}</span><small>{report.employee.job_title} · {report.department.name}</small></div><em className={report.status}>{report.status==='pending'?'Pendente':report.status==='approved'?'Aprovado':'Correção solicitada'}</em></header><h2>{report.summary}</h2><p>{report.tasks_performed}</p><footer>{report.work_location&&<span><MapPin/>{report.work_location}</span>}<span><Clock3/>{report.start_time?.slice(0,5)||'--:--'} — {report.end_time?.slice(0,5)||'--:--'}</span><span className={report.work_status}><CheckCircle2/>{report.work_status==='completed'?'Concluído':report.work_status==='blocked'?'Bloqueado':'Em andamento'}</span></footer>{report.review_notes&&<div className="review-note"><CircleAlert/>{report.review_notes}</div>}</div>{(canReview||report.status!=='approved')&&<div className="report-actions"><button onClick={()=>setEditingReport(report)}><Edit3/> Editar</button>{canReview&&report.status!=='approved'&&<button className="approve" onClick={()=>review(report.id,'approve')}><Check/> Aprovar</button>}{canReview&&report.status!=='approved'&&<button onClick={()=>review(report.id,'request_correction')}><Edit3/> Solicitar correção</button>}</div>}</article>)}{!filtered.length&&<div className="empty-module"><FileClock/><strong>Nenhum relatório encontrado</strong><p>Não existem relatórios para o filtro selecionado.</p></div>}</section>}{formOpen&&<Modal wide title="Novo relatório diário" subtitle="O relatório será enviado automaticamente para RH e supervisão." onClose={()=>setFormOpen(false)}><DailyReportForm employees={employees} onSaved={load} onClose={()=>setFormOpen(false)}/></Modal>}{editingReport&&<Modal wide title="Editar relatório diário" subtitle="A alteração volta a colocar o relatório em revisão." onClose={()=>setEditingReport(null)}><DailyReportForm employees={employees} report={editingReport} onSaved={load} onClose={()=>setEditingReport(null)}/></Modal>}</>
}

function PerformanceForm({employees,onSaved,onClose}:{employees:Employee[];onSaved:()=>void;onClose:()=>void}){
  const [busy,setBusy]=useState(false),[error,setError]=useState<string|null>(null),[scores,setScores]=useState<Record<string,number>>({punctuality:4,productivity:4,work_quality:4,task_completion:4,reports_score:4,supervisor_score:4});const average=Object.values(scores).reduce((sum,value)=>sum+value,0)/6*20
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();setBusy(true);setError(null);const data=Object.fromEntries(new FormData(event.currentTarget)) as Record<string,string>;try{await api.createPerformance({...data,...scores});onSaved();onClose()}catch(reason){setError(reason instanceof ApiError?reason.message:'Não foi possível guardar a avaliação.')}finally{setBusy(false)}}
  const labels:Record<string,string>={punctuality:'Pontualidade',productivity:'Produtividade',work_quality:'Qualidade do trabalho',task_completion:'Cumprimento de tarefas',reports_score:'Relatórios enviados',supervisor_score:'Avaliação do supervisor'}
  return <form className="module-form" onSubmit={submit}>{error&&<ErrorBanner message={error}/>}<div className="performance-form-head"><div><Award/><span>Score calculado</span><strong>{average.toFixed(1)}%</strong></div><label><span>Trabalhador</span><select name="employee_id" required>{employees.map(item=><option key={item.id} value={item.id}>{item.full_name} · {item.job_title}</option>)}</select></label><label><span>Período</span><input name="period" type="month" defaultValue={new Date().toISOString().slice(0,7)} required /></label></div><div className="score-inputs">{Object.entries(labels).map(([key,label])=><label key={key}><span>{label}</span><div><input type="range" min="0" max="5" step="0.1" value={scores[key]} onChange={e=>setScores(current=>({...current,[key]:Number(e.target.value)}))}/><strong>{scores[key].toFixed(1)}</strong></div></label>)}</div><label className="full-textarea"><span>Observações do supervisor</span><textarea name="supervisor_notes" rows={4} placeholder="Pontos fortes, oportunidades e plano de evolução..." /></label><input type="hidden" name="status" value="published"/><div className="module-form-actions"><button type="button" className="module-secondary-button" onClick={onClose}>Cancelar</button><SubmitButton busy={busy}><Star/> Publicar avaliação</SubmitButton></div></form>
}

export function PerformancePage(){
  const {user}=useAuth();const [reviews,setReviews]=useState<PerformanceReview[]>([]),[employees,setEmployees]=useState<Employee[]>([]),[loading,setLoading]=useState(true),[error,setError]=useState<string|null>(null),[formOpen,setFormOpen]=useState(false);const canManage=hasPermission(user?.permissions??[],'performance.manage')
  async function load(){setLoading(true);setError(null);try{const [items,people]=await Promise.all([api.performance(),api.employees()]);setReviews(items);setEmployees(people)}catch(reason){setError(reason instanceof ApiError?reason.message:'Falha ao carregar avaliações.')}finally{setLoading(false)}}useEffect(()=>{void load()},[])
  const average=reviews.length?reviews.reduce((sum,item)=>sum+Number(item.overall_score),0)/reviews.length:0
  return <><PageHeader eyebrow="Pessoas · Desempenho" title="Desempenho e produtividade" description="Avaliações mensais, ranking interno e evolução das equipas." action={canManage&&<button className="module-primary-button" onClick={()=>setFormOpen(true)}><Plus/> Nova avaliação</button>}/>{error&&<ErrorBanner message={error} onRetry={load}/>}<section className="performance-summary"><article><span><Award/></span><p>Score médio<strong>{average.toFixed(1)}%</strong><small>{reviews.length} avaliações publicadas</small></p></article><article><span><Star/></span><p>Melhor resultado<strong>{reviews.length?Number(reviews[0].overall_score).toFixed(1):'0.0'}%</strong><small>{reviews[0]?.employee.full_name??'Sem dados'}</small></p></article><article><span><CalendarCheck/></span><p>Período atual<strong>{new Date().toLocaleDateString('pt-AO',{month:'long'})}</strong><small>Fecho mensal ativo</small></p></article></section>{loading?<LoadingRows/>:<section className="module-panel table-panel"><div className="responsive-table"><table><thead><tr><th>#</th><th>Trabalhador</th><th>Período</th><th>Pontualidade</th><th>Produtividade</th><th>Qualidade</th><th>Score geral</th></tr></thead><tbody>{reviews.map((review,index)=><tr key={review.id}><td><span className={cn('ranking-number',index<3&&'top')}>{index+1}</span></td><td><div className="table-person"><span>{review.employee.full_name.split(' ').map(p=>p[0]).slice(0,2).join('')}</span><p><strong>{review.employee.full_name}</strong><small>{review.employee.department.name} · {review.employee.job_title}</small></p></div></td><td>{review.period}</td><td><Score value={Number(review.punctuality)}/></td><td><Score value={Number(review.productivity)}/></td><td><Score value={Number(review.work_quality)}/></td><td><strong className="overall-score">{Number(review.overall_score).toFixed(1)}%</strong></td></tr>)}</tbody></table></div></section>}{formOpen&&<Modal wide title="Nova avaliação de desempenho" subtitle="Classifique cada dimensão de 0 a 5. O score geral é calculado automaticamente." onClose={()=>setFormOpen(false)}><PerformanceForm employees={employees} onSaved={load} onClose={()=>setFormOpen(false)}/></Modal>}</>
}

function Score({value}:{value:number}){return <div className="mini-score"><span><i style={{width:`${value/5*100}%`}}/></span><strong>{value.toFixed(1)}</strong></div>}
