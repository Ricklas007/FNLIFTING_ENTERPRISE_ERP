import { useEffect, useState, type FormEvent } from 'react'
import { Download, Edit3, Eye, FileBadge2, HardHat, Plus, QrCode, Send, ShieldCheck, Stamp, UserPlus } from 'lucide-react'

import { ErrorBanner, hasPermission, LoadingRows, Modal, PageHeader, SubmitButton } from '@/pages/HRPages'
import { api, ApiError } from '@/services/api'
import { useAuth } from '@/store/AuthContext'
import { cn } from '@/lib/utils'
import type { Certificate, Employee, Inspection, TechnicalSignatory } from '@/types'


const labels: Record<string, string> = { draft: 'Rascunho', issued: 'Emitido', rejected: 'Rejeitado' }

async function imageDataUrl(value: FormDataEntryValue | null) {
  if (!(value instanceof File) || !value.size) return undefined
  return await new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(new Error('Não foi possível ler a imagem.'))
    reader.readAsDataURL(value)
  })
}

function SignatoryManager({ records, employees, onSaved, onClose }: { records: TechnicalSignatory[]; employees: Employee[]; onSaved: () => Promise<void>; onClose: () => void }) {
  const [selectedId, setSelectedId] = useState('new')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const selected = records.find(item => item.id === selectedId)
  const availableEmployees = employees.filter(employee => !records.some(record => record.employee_id === employee.id))

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(null)
    const data = new FormData(event.currentTarget)
    try {
      const signature = await imageDataUrl(data.get('signature_file'))
      const stamp = await imageDataUrl(data.get('stamp_file'))
      const payload: Record<string, unknown> = {
        inspector_code: String(data.get('inspector_code')),
        qualifications: String(data.get('qualifications')),
        employer_name: String(data.get('employer_name') || 'FNLIFTING ANGOLA'),
        employer_address: String(data.get('employer_address') || '') || null,
        can_inspect: data.get('can_inspect') === 'on', can_approve: data.get('can_approve') === 'on',
        status: String(data.get('status')),
      }
      if (signature) payload.signature_data_url = signature
      if (stamp) payload.stamp_data_url = stamp
      if (selected) await api.updateSignatory(selected.id, payload)
      else { payload.employee_id = String(data.get('employee_id')); await api.createSignatory(payload) }
      await onSaved(); setSelectedId('new')
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : reason instanceof Error ? reason.message : 'Não foi possível guardar o perfil técnico.')
    } finally { setBusy(false) }
  }

  return <div className="signatory-manager">
    <aside className="signatory-list">
      <button type="button" className={selectedId === 'new' ? 'active' : ''} onClick={() => setSelectedId('new')}><UserPlus /> Registar outro inspetor</button>
      {records.map(item => <button type="button" key={item.id} className={selectedId === item.id ? 'active' : ''} onClick={() => setSelectedId(item.id)}><span><strong>{item.employee.full_name}</strong><small>{item.inspector_code} · {item.can_approve ? 'Aprovador' : 'Inspetor'}</small></span><i className={item.signature_available && item.stamp_available ? 'ready' : ''}>{item.signature_available && item.stamp_available ? 'Pronto' : 'Incompleto'}</i></button>)}
    </aside>
    <form className="module-form signatory-form" key={selectedId} onSubmit={submit}>
      {error && <ErrorBanner message={error} />}
      {!selected && <label><span>Trabalhador</span><select name="employee_id" required defaultValue=""><option value="" disabled>Selecione um trabalhador</option>{availableEmployees.map(item => <option key={item.id} value={item.id}>{item.full_name} · {item.job_title}</option>)}</select></label>}
      {selected && <div className="certificate-rule"><HardHat /><p><strong>{selected.employee.full_name}</strong><span>{selected.employee.job_title}</span></p></div>}
      <div className="module-form-grid two">
        <label><span>Código / iniciais</span><input name="inspector_code" required defaultValue={selected?.inspector_code || ''} placeholder="Ex.: PO" /></label>
        <label><span>Estado</span><select name="status" defaultValue={selected?.status || 'active'}><option value="active">Ativo</option><option value="inactive">Inativo</option></select></label>
        <label className="span-two"><span>Qualificações</span><textarea name="qualifications" rows={3} required defaultValue={selected?.qualifications || ''} /></label>
        <label><span>Entidade empregadora</span><input name="employer_name" defaultValue={selected?.employer_name || 'FNLIFTING ANGOLA'} /></label>
        <label><span>Endereço da entidade</span><input name="employer_address" defaultValue={selected?.employer_address || ''} /></label>
        <label><span>Imagem da assinatura</span><input name="signature_file" type="file" accept="image/png,image/jpeg" required={!selected?.signature_available} /><small>PNG/JPEG até 2,5 MB</small></label>
        <label><span>Imagem do carimbo</span><input name="stamp_file" type="file" accept="image/png,image/jpeg" required={!selected?.stamp_available} /><small>PNG/JPEG até 2,5 MB</small></label>
      </div>
      <div className="signatory-permissions"><label><input name="can_inspect" type="checkbox" defaultChecked={selected?.can_inspect ?? true} /> Pode assinar inspeções</label><label><input name="can_approve" type="checkbox" defaultChecked={selected?.can_approve ?? false} /> Pode autenticar certificados</label></div>
      <div className="module-form-actions"><button type="button" className="module-secondary-button" onClick={onClose}>Fechar</button><SubmitButton busy={busy}><Stamp /> Guardar assinatura e carimbo</SubmitButton></div>
    </form>
  </div>
}

function CertificateEditForm({ certificate, approvers, onSaved, onClose }: { certificate: Certificate; approvers: TechnicalSignatory[]; onSaved: () => Promise<void>; onClose: () => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(null)
    const data = new FormData(event.currentTarget)
    try {
      await api.updateCertificate(certificate.id, {
        document_type: String(data.get('document_type')),
        approver_signatory_id: String(data.get('approver_signatory_id') || '') || null,
        service_order_no: String(data.get('service_order_no') || '') || null,
        report_no: String(data.get('report_no') || '') || null,
        identification_no: String(data.get('identification_no') || '') || null,
        standard_reference: String(data.get('standard_reference')),
        colour_code: String(data.get('colour_code') || '') || null,
        reason_code: String(data.get('reason_code')),
        safe_to_use: data.get('safe_to_use') === 'on',
      })
      await onSaved(); onClose()
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Não foi possível editar o rascunho.')
    } finally { setBusy(false) }
  }
  return <form className="module-form" onSubmit={submit}>
    {error && <ErrorBanner message={error} />}
    <div className="certificate-rule"><FileBadge2 /><p><strong>{certificate.certificate_no}</strong><span>{certificate.equipment.name} · {certificate.client.name}</span></p></div>
    <div className="module-form-grid two">
      <label className="span-two"><span>Tipo de documento</span><input name="document_type" defaultValue={certificate.document_type} required /></label>
      <label><span>Supervisor autenticador</span><select name="approver_signatory_id" defaultValue={certificate.approver_signatory_id || ''} required>{approvers.map(item => <option key={item.id} value={item.id}>{item.employee.full_name} · {item.inspector_code}</option>)}</select></label>
      <label><span>Ordem de serviço</span><input name="service_order_no" defaultValue={certificate.service_order_no || ''} /></label>
      <label><span>N.º do relatório</span><input name="report_no" defaultValue={certificate.report_no || ''} /></label>
      <label><span>Identificação</span><input name="identification_no" defaultValue={certificate.identification_no || ''} /></label>
      <label className="span-two"><span>Norma aplicável</span><input name="standard_reference" defaultValue={certificate.standard_reference} required /></label>
      <label><span>Código de cor</span><input name="colour_code" defaultValue={certificate.colour_code || ''} /></label>
      <label><span>Razão do exame</span><select name="reason_code" defaultValue={certificate.reason_code}><option value="A">A · Instalação</option><option value="B">B · 6 meses</option><option value="C">C · Anual</option><option value="D">D · Esquema escrito</option><option value="E">E · Circunstância excecional</option></select></label>
    </div>
    <label className="signatory-check"><input name="safe_to_use" type="checkbox" defaultChecked={certificate.safe_to_use} /> Equipamento seguro para utilização</label>
    <div className="module-form-actions"><button type="button" className="module-secondary-button" onClick={onClose}>Cancelar</button><SubmitButton busy={busy}><Edit3 /> Guardar rascunho</SubmitButton></div>
  </form>
}

export function CertificatesPage() {
  const { user } = useAuth()
  const [records, setRecords] = useState<Certificate[]>([])
  const [inspections, setInspections] = useState<Inspection[]>([])
  const [signatories, setSignatories] = useState<TechnicalSignatory[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [formOpen, setFormOpen] = useState(false)
  const [signatoryOpen, setSignatoryOpen] = useState(false)
  const [editing, setEditing] = useState<Certificate | null>(null)
  const [preview, setPreview] = useState<{ title: string; url: string } | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const canManage = hasPermission(user?.permissions ?? [], 'certificates.manage')
  const external = user?.account_type === 'external'

  async function load() {
    setLoading(true); setError(null)
    try {
      const [certs, inspectionRecords, people, staff] = await Promise.all([
        api.certificates(), canManage ? api.inspections() : Promise.resolve([]),
        canManage ? api.signatories() : Promise.resolve([]), canManage ? api.employees() : Promise.resolve([]),
      ])
      setRecords(certs); setInspections(inspectionRecords); setSignatories(people); setEmployees(staff)
    } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Falha ao carregar certificados.') }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [])
  useEffect(() => () => { if (preview?.url) URL.revokeObjectURL(preview.url) }, [preview])

  const available = inspections.filter(item => item.status === 'approved' && !records.some(cert => cert.inspection_id === item.id))
  const approvers = signatories.filter(item => item.can_approve && item.status === 'active' && item.signature_available && item.stamp_available)

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusyId('create'); setError(null)
    const data = new FormData(event.currentTarget)
    try {
      await api.createCertificate({
        inspection_id: String(data.get('inspection_id')), approver_signatory_id: String(data.get('approver_signatory_id')),
        service_order_no: String(data.get('service_order_no') || '') || null, report_no: String(data.get('report_no') || '') || null,
        identification_no: String(data.get('identification_no') || '') || null, standard_reference: String(data.get('standard_reference')),
        colour_code: String(data.get('colour_code') || '') || null, reason_code: String(data.get('reason_code')), safe_to_use: data.get('safe_to_use') === 'on',
      })
      setFormOpen(false); await load()
    } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Não foi possível criar o certificado.') }
    finally { setBusyId(null) }
  }
  async function issue(item: Certificate) { setBusyId(item.id); setError(null); try { await api.issueCertificate(item.id); await load() } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Não foi possível emitir o certificado.') } finally { setBusyId(null) } }
  async function downloadPdf(item: Certificate) { setBusyId(item.id); setError(null); try { await api.downloadCertificate(item.id, item.certificate_no) } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Não foi possível descarregar o PDF.') } finally { setBusyId(null) } }
  async function previewPdf(item: Certificate) { setBusyId(item.id); setError(null); try { const url = await api.previewCertificate(item.id); setPreview(current => { if (current?.url) URL.revokeObjectURL(current.url); return { title: item.certificate_no, url } }) } catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Não foi possível pré-visualizar o certificado.') } finally { setBusyId(null) } }

  const action = canManage && <div className="page-header-actions"><button className="module-secondary-button" onClick={() => setSignatoryOpen(true)}><Stamp /> Inspetores e assinaturas</button><button className="module-primary-button" onClick={() => setFormOpen(true)} disabled={!available.length || !approvers.length}><Plus /> Novo certificado</button></div>
  return <>
    <PageHeader eyebrow={external ? 'Portal do cliente · Documentos' : 'Operações · Certificados'} title={external ? 'Certificados da empresa' : 'Certificados técnicos'} description={external ? 'Consulte a validade e descarregue os certificados emitidos para a sua empresa.' : 'Modelo oficial FNLIFTING com assinatura, carimbo, QR e autenticação técnica automática.'} action={action} />
    {error && <ErrorBanner message={error} onRetry={load} />}
    {loading ? <LoadingRows /> : <section className="certificates-grid">{records.map(item => { const days = Math.ceil((new Date(item.expires_at).getTime() - Date.now()) / 86400000); return <article className="certificate-card" key={item.id}><div className="certificate-ribbon"><FileBadge2 /></div><header><span className={cn('ops-status', item.status)}>{labels[item.status] ?? item.status}</span><span>R{String(item.revision).padStart(2, '0')}</span></header><small>{item.document_type}</small><h2>{item.certificate_no}</h2><p><strong>{item.equipment.name}</strong><span>{item.client.name} · {item.equipment.code}</span></p>{item.approver_signatory && <div className="certificate-signer"><Stamp /><span>Autenticado por <strong>{item.approver_signatory.employee.full_name}</strong></span></div>}<div className="certificate-dates"><span><small>Emitido</small><strong>{new Date(`${item.issued_at}T00:00:00`).toLocaleDateString('pt-AO')}</strong></span><span><small>Válido até</small><strong>{new Date(`${item.expires_at}T00:00:00`).toLocaleDateString('pt-AO')}</strong></span></div><div className={cn('validity-bar', days < 45 && 'warning')}><i /><span>{days > 0 ? `${days} dias restantes` : 'Expirado'}</span></div><footer><span><QrCode /> Verificação QR</span><button onClick={() => previewPdf(item)} disabled={busyId === item.id}><Eye /> Ver</button>{item.status === 'draft' && canManage && <button onClick={() => setEditing(item)} disabled={busyId === item.id}><Edit3 /> Editar</button>}{item.status === 'draft' && canManage ? <button onClick={() => issue(item)} disabled={busyId === item.id}><Send /> Emitir</button> : item.status === 'issued' ? <button onClick={() => downloadPdf(item)} disabled={busyId === item.id}><Download /> PDF</button> : null}</footer></article> })}</section>}
    {formOpen && <Modal wide title="Novo certificado oficial" subtitle="Os dados, assinatura do inspetor e autenticação do supervisor serão aplicados automaticamente." onClose={() => setFormOpen(false)}><form className="module-form" onSubmit={create}><div className="module-form-grid two"><label className="span-two"><span>Inspeção aprovada</span><select name="inspection_id" required>{available.map(item => <option key={item.id} value={item.id}>{item.inspection_no} · {item.equipment.name} · {item.client.name}</option>)}</select></label><label><span>Supervisor autenticador</span><select name="approver_signatory_id" required>{approvers.map(item => <option key={item.id} value={item.id}>{item.employee.full_name} · {item.inspector_code}</option>)}</select></label><label><span>Ordem de serviço</span><input name="service_order_no" placeholder="Automática se vazio" /></label><label><span>N.º do relatório</span><input name="report_no" placeholder="Automático se vazio" /></label><label><span>Identificação</span><input name="identification_no" placeholder="Série do equipamento" /></label><label className="span-two"><span>Norma aplicável</span><input name="standard_reference" defaultValue="BS EN 1492-1:2000+A1:2008" required /></label><label><span>Código de cor</span><input name="colour_code" defaultValue="Blue/Black" /></label><label><span>Razão do exame</span><select name="reason_code" defaultValue="C"><option value="A">A · Instalação</option><option value="B">B · 6 meses</option><option value="C">C · Anual</option><option value="D">D · Esquema escrito</option><option value="E">E · Circunstância excecional</option></select></label></div><label className="signatory-check"><input name="safe_to_use" type="checkbox" defaultChecked /> Equipamento seguro para utilização</label><div className="certificate-rule"><ShieldCheck /><p><strong>Emissão protegida</strong><span>O sistema bloqueará o documento se faltar assinatura, carimbo, inspetor ou supervisor autorizado.</span></p></div><div className="module-form-actions"><button type="button" className="module-secondary-button" onClick={() => setFormOpen(false)}>Cancelar</button><SubmitButton busy={busyId === 'create'}><FileBadge2 /> Criar rascunho</SubmitButton></div></form></Modal>}
    {editing && <Modal wide title="Editar certificado em rascunho" subtitle="Revise dados técnicos antes da emissão e assinatura final." onClose={() => setEditing(null)}><CertificateEditForm certificate={editing} approvers={approvers} onSaved={load} onClose={() => setEditing(null)} /></Modal>}
    {preview && <Modal wide title={`Pré-visualização · ${preview.title}`} subtitle="Confirme o documento dentro do sistema antes de descarregar ou emitir." onClose={() => setPreview(current => { if (current?.url) URL.revokeObjectURL(current.url); return null })}><iframe className="document-preview-frame" src={preview.url} title={preview.title} /></Modal>}
    {signatoryOpen && <Modal wide title="Inspetores, assinaturas e carimbos" subtitle="Cada documento será assinado com o perfil técnico associado ao responsável pela inspeção." onClose={() => setSignatoryOpen(false)}><SignatoryManager records={signatories} employees={employees} onSaved={load} onClose={() => setSignatoryOpen(false)} /></Modal>}
  </>
}
