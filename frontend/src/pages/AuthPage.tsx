import { useState, type FormEvent } from 'react'
import {
  ArrowLeft, ArrowRight, AtSign, Building2, CheckCircle2, CircleHelp, Eye,
  EyeOff, Fingerprint, Headphones, KeyRound, LockKeyhole, ShieldCheck, UserRound,
} from 'lucide-react'
import { BrandLogo } from '@/components/BrandLogo'
import { api, ApiError } from '@/services/api'
import { useAuth } from '@/store/useAuth'

type View = 'login' | 'register' | 'forgot' | 'mfa'
type Portal = 'staff' | 'client'

const roles = [
  ['administrator', 'Administrador'], ['general_director', 'Diretor Geral'],
  ['technician', 'Técnico'], ['inspector', 'Inspetor'], ['driver', 'Motorista'],
  ['hr', 'Recursos Humanos'], ['finance', 'Financeiro'], ['operations', 'Operações'],
  ['logistics', 'Logística'], ['supervisor', 'Supervisor'], ['asset_manager', 'Gestor de Património'],
  ['security', 'Segurança'], ['auditor', 'Auditor'], ['visitor', 'Visitante'],
]

function Field({ label, icon, children }: { label: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <label className="auth-field">
      <span className="auth-label">{label}</span>
      <span className="auth-input-wrap"><span className="auth-field-icon">{icon}</span>{children}</span>
    </label>
  )
}

export function AuthPage() {
  const { login, completeMfaLogin } = useAuth()
  const [view, setView] = useState<View>('login')
  const [portal, setPortal] = useState<Portal>('staff')
  const [showPassword, setShowPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<{ type: 'error' | 'success'; text: string } | null>(null)
  const [mfaChallenge, setMfaChallenge] = useState<{ id: string; hint: string; remember: boolean } | null>(null)

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setMessage(null)
    setBusy(true)
    const data = new FormData(event.currentTarget)
    try {
      const remember = data.get('remember') === 'on'
      const challenge = await login(String(data.get('identifier')), String(data.get('password')), portal, remember)
      if (challenge?.mfa_required) {
        setMfaChallenge({ id: challenge.challenge_id, hint: challenge.user_hint, remember })
        setView('mfa')
        setMessage({ type: 'success', text: 'Introduza o código MFA para concluir o acesso.' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: error instanceof ApiError ? error.message : 'Não foi possível iniciar sessão.' })
    } finally { setBusy(false) }
  }

  async function handleMfa(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!mfaChallenge) return
    setMessage(null)
    setBusy(true)
    const data = new FormData(event.currentTarget)
    try {
      await completeMfaLogin(mfaChallenge.id, String(data.get('code')), mfaChallenge.remember)
    } catch (error) {
      setMessage({ type: 'error', text: error instanceof ApiError ? error.message : 'Não foi possível validar o MFA.' })
    } finally { setBusy(false) }
  }

  async function handleRegister(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setMessage(null)
    setBusy(true)
    const data = Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>
    try {
      const result = await api.register({
        full_name: data.full_name, email: data.email, username: data.username,
        phone: data.phone || undefined, password: data.password,
        requested_role: portal === 'client' ? 'client_external' : data.requested_role,
        account_type: portal === 'client' ? 'external' : 'internal',
        company_name: portal === 'client' ? data.company_name : undefined,
        company_nif: portal === 'client' ? data.company_nif : undefined,
      })
      setMessage({ type: 'success', text: result.message })
      event.currentTarget.reset()
    } catch (error) {
      setMessage({ type: 'error', text: error instanceof ApiError ? error.message : 'Não foi possível criar o pedido.' })
    } finally { setBusy(false) }
  }

  async function handleForgot(event: FormEvent) {
    event.preventDefault(); setBusy(true)
    try {
      const result = await api.forgotPassword()
      setMessage({ type: 'success', text: result.message })
    } catch (error) {
      setMessage({ type: 'error', text: error instanceof ApiError ? error.message : 'Não foi possível registar o pedido.' })
    } finally { setBusy(false) }
  }

  const isLogin = view === 'login'
  return (
    <main className="auth-page">
      <div className="auth-bg" />
      <div className="auth-map" />
      <div className="auth-orb auth-orb-one" /><div className="auth-orb auth-orb-two" />
      <section className="auth-brand-panel">
        <BrandLogo className="auth-main-logo" />
        <div className="auth-brand-copy">
          <span className="eyebrow"><span /> Oil & Gas operations platform</span>
          <h1>Operações críticas.<br /><em>Uma visão completa.</em></h1>
          <p>Inspeção, frota, equipas e finanças num único ambiente empresarial seguro, preparado para trabalhar online e offline.</p>
          <div className="auth-trust-row">
            <span><ShieldCheck /> Acesso protegido</span><span><Fingerprint /> Auditoria integral</span><span><Building2 /> Multiempresa</span>
          </div>
        </div>
      </section>

      <section className="auth-form-panel">
        <div className="auth-mobile-logo"><BrandLogo compact /></div>
        <div className="auth-card">
          {view !== 'login' && (
            <button type="button" className="back-button" onClick={() => { setView('login'); setMessage(null); setMfaChallenge(null) }}><ArrowLeft size={16} /> Voltar ao login</button>
          )}
          <div className="auth-heading">
            <span className="auth-heading-icon">{view === 'register' ? <UserRound /> : view === 'forgot' ? <KeyRound /> : <LockKeyhole />}</span>
            <div>
              <p className="auth-kicker">FNL Enterprise ERP</p>
              <h2>{view === 'register' ? 'Solicitar acesso' : view === 'forgot' ? 'Recuperar acesso' : view === 'mfa' ? 'Verificação MFA' : 'Bem-vindo de volta'}</h2>
            </div>
          </div>
          <p className="auth-subtitle">
            {view === 'register' ? 'Preencha os dados. A conta será validada pelo Administrador ou RH.' : view === 'forgot' ? 'Registe o pedido para redefinir a sua palavra-passe.' : 'Selecione o portal e introduza as suas credenciais.'}
          </p>

          {view !== 'forgot' && view !== 'mfa' && (
            <div className="portal-switch" role="tablist" aria-label="Tipo de acesso">
              <button type="button" className={portal === 'staff' ? 'active' : ''} onClick={() => setPortal('staff')}><ShieldCheck size={16} /> Colaborador FNL</button>
              <button type="button" className={portal === 'client' ? 'active' : ''} onClick={() => setPortal('client')}><Building2 size={16} /> Empresa cliente</button>
            </div>
          )}

          {message && <div className={`auth-message ${message.type}`}><span>{message.type === 'success' ? <CheckCircle2 /> : <CircleHelp />}</span>{message.text}</div>}

          {isLogin && (
            <form className="auth-form" onSubmit={handleLogin}>
              <Field label="Email ou utilizador" icon={<AtSign size={18} />}>
                <input name="identifier" autoComplete="username" required placeholder={portal === 'staff' ? 'admin@fnlifting.com ou utilizador' : 'email@empresa.co.ao'} />
              </Field>
              <Field label="Palavra-passe" icon={<KeyRound size={18} />}>
                <input name="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" required minLength={8} placeholder="Introduza a sua palavra-passe" />
                <button className="password-toggle" type="button" onClick={() => setShowPassword(value => !value)} aria-label="Mostrar palavra-passe">{showPassword ? <EyeOff /> : <Eye />}</button>
              </Field>
              <div className="auth-options">
                <label className="remember"><input type="checkbox" name="remember" /><span /> Lembrar-me</label>
                <button type="button" onClick={() => { setView('forgot'); setMessage(null) }}>Esqueci a palavra-passe</button>
              </div>
              <button className="primary-auth-button" type="submit" disabled={busy}>{busy ? <span className="button-spinner" /> : <>Entrar no sistema <ArrowRight size={19} /></>}</button>
              <div className="auth-divider"><span>Primeiro acesso?</span></div>
              <button className="secondary-auth-button" type="button" onClick={() => { setView('register'); setMessage(null) }}><UserRound size={17} /> Criar pedido de conta</button>
            </form>
          )}

          {view === 'mfa' && (
            <form className="auth-form" onSubmit={handleMfa}>
              <Field label="Código MFA" icon={<Fingerprint size={18} />}>
                <input name="code" inputMode="numeric" autoComplete="one-time-code" required minLength={6} placeholder="000000 ou código de recuperação" />
              </Field>
              <button className="primary-auth-button" type="submit" disabled={busy}>{busy ? <span className="button-spinner" /> : <>Validar e entrar <ArrowRight size={19} /></>}</button>
            </form>
          )}

          {view === 'register' && (
            <form className="auth-form register-form" onSubmit={handleRegister}>
              <div className="form-grid">
                <Field label="Nome completo" icon={<UserRound size={17} />}><input name="full_name" required minLength={3} placeholder="Nome e apelido" /></Field>
                <Field label="Utilizador" icon={<Fingerprint size={17} />}><input name="username" required minLength={3} placeholder="nome.apelido" /></Field>
              </div>
              <Field label="Email" icon={<AtSign size={17} />}><input name="email" type="email" required placeholder="nome@empresa.com" /></Field>
              {portal === 'client' ? (
                <div className="form-grid">
                  <Field label="Empresa" icon={<Building2 size={17} />}><input name="company_name" required placeholder="Nome da empresa" /></Field>
                  <Field label="NIF" icon={<Fingerprint size={17} />}><input name="company_nif" required placeholder="NIF da empresa" /></Field>
                </div>
              ) : (
                <label className="auth-field"><span className="auth-label">Área de atuação</span><span className="auth-input-wrap"><span className="auth-field-icon"><Building2 size={17} /></span><select name="requested_role" required defaultValue="technician">{roles.map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></span></label>
              )}
              <Field label="Palavra-passe" icon={<KeyRound size={17} />}><input name="password" type="password" required minLength={10} placeholder="Mínimo 10 caracteres" /></Field>
              <button className="primary-auth-button" type="submit" disabled={busy}>{busy ? <span className="button-spinner" /> : <>Enviar pedido <ArrowRight size={19} /></>}</button>
            </form>
          )}

          {view === 'forgot' && (
            <form className="auth-form" onSubmit={handleForgot}>
              <Field label="Email da conta" icon={<AtSign size={18} />}><input type="email" required placeholder="nome@empresa.com" /></Field>
              <button className="primary-auth-button" type="submit" disabled={busy}>{busy ? <span className="button-spinner" /> : <>Registar pedido <ArrowRight size={19} /></>}</button>
            </form>
          )}
        </div>
        <div className="auth-support"><Headphones size={15} /> Necessita de ajuda? <a href="mailto:suporte@fnlifting.com">Contacte o suporte</a></div>
        <p className="auth-copyright">© 2026 FNLIFTING ANGOLA. Ambiente protegido e auditado.</p>
      </section>
    </main>
  )
}
