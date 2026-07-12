import logoDark from '@/assets/fnl-logo-dark.png'
import { cn } from '@/lib/utils'

export function BrandLogo({ compact = false, className }: { compact?: boolean; className?: string }) {
  if (compact) {
    return (
      <div className={cn('flex items-center gap-3', className)} aria-label="FNLIFTING Enterprise ERP">
        <div className="brand-mark"><span>FN</span></div>
        <div className="leading-none">
          <strong className="text-[17px] tracking-[.12em] text-white">LIFTING</strong>
          <p className="mt-1 text-[8px] tracking-[.27em] text-slate-500">ENTERPRISE ERP</p>
        </div>
      </div>
    )
  }
  return <img className={cn('block object-contain', className)} src={logoDark} alt="FNLIFTING Enterprise ERP" />
}

