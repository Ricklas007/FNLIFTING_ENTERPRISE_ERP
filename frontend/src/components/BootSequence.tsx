import { useEffect, useState, type ReactNode } from 'react'
import { CheckCircle2, Database, LockKeyhole, ShieldCheck, Wifi } from 'lucide-react'
import { BrandLogo } from '@/components/BrandLogo'

type Stage = 'splash' | 'loading' | 'ready'

export function BootSequence({ children }: { children: ReactNode }) {
  const [stage, setStage] = useState<Stage>('splash')
  const [progress, setProgress] = useState(8)
  const [message, setMessage] = useState('A iniciar ambiente seguro')

  useEffect(() => {
    const splashTimer = window.setTimeout(() => setStage('loading'), 1900)
    return () => window.clearTimeout(splashTimer)
  }, [])

  useEffect(() => {
    if (stage !== 'loading') return
    const steps = [
      [28, 'A verificar base de dados local'],
      [52, 'A carregar permissões e módulos'],
      [76, 'A preparar ambiente offline'],
      [94, 'A concluir verificações de segurança'],
      [100, 'Sistema pronto'],
    ] as const
    let index = 0
    const timer = window.setInterval(() => {
      const step = steps[index++]
      if (!step) return
      setProgress(step[0])
      setMessage(step[1])
      if (step[0] === 100) {
        window.clearInterval(timer)
        window.setTimeout(() => setStage('ready'), 420)
      }
    }, 320)
    return () => window.clearInterval(timer)
  }, [stage])

  if (stage === 'ready') return <>{children}</>

  if (stage === 'splash') {
    return (
      <div className="splash-screen">
        <div className="splash-aurora" />
        <BrandLogo className="splash-logo" />
        <p className="splash-version">ENTERPRISE MANAGEMENT SYSTEM <span>•</span> v0.1</p>
      </div>
    )
  }

  return (
    <div className="loading-screen">
      <div className="loading-grid" />
      <div className="loading-orbit loading-orbit-one" />
      <div className="loading-orbit loading-orbit-two" />
      <div className="relative z-10 flex w-full max-w-md flex-col items-center px-8">
        <BrandLogo compact className="mb-14 scale-125" />
        <div className="loader-emblem">
          {progress < 100 ? <ShieldCheck size={34} /> : <CheckCircle2 size={34} />}
          <span className="loader-pulse" />
        </div>
        <h1 className="mt-8 text-xl font-semibold text-white">A preparar o seu espaço de trabalho</h1>
        <p className="mt-2 text-sm text-slate-400">{message}</p>
        <div className="mt-8 h-1.5 w-full overflow-hidden rounded-full bg-white/5">
          <div className="h-full rounded-full bg-gradient-to-r from-blue-700 via-cyan-400 to-blue-500 transition-all duration-500" style={{ width: `${progress}%` }} />
        </div>
        <div className="mt-4 flex w-full justify-between text-[11px] font-medium uppercase tracking-widest text-slate-600">
          <span>{progress}%</span><span>Local-first secure boot</span>
        </div>
        <div className="mt-12 flex items-center gap-7 text-slate-600">
          <span className="flex items-center gap-2 text-xs"><Database size={14} /> SQLite</span>
          <span className="flex items-center gap-2 text-xs"><LockKeyhole size={14} /> RBAC</span>
          <span className="flex items-center gap-2 text-xs"><Wifi size={14} /> Offline ready</span>
        </div>
      </div>
    </div>
  )
}

