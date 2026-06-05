import { clsx } from 'clsx'
import type { Rank } from '../../types'

interface ProgressBarProps {
  value: number // 0-100
  max?: number
  label?: string
  showLabel?: boolean
  size?: 'sm' | 'md'
  variant?: 'brand' | 'rank'
  rank?: Rank
  className?: string
}

const rankBarColor: Record<Rank, string> = {
  nuevo: 'bg-slate-400',
  confiable: 'bg-blue-400',
  experto: 'bg-emerald-400',
  elite: 'bg-gradient-to-r from-amber-500 to-amber-300',
}

export default function ProgressBar({
  value,
  max = 100,
  label,
  showLabel = false,
  size = 'sm',
  variant = 'brand',
  rank,
  className,
}: ProgressBarProps) {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100)

  return (
    <div className={className}>
      {(label || showLabel) && (
        <div className="flex justify-between items-center mb-1">
          {label && <span className="text-xs text-neutral-500">{label}</span>}
          {showLabel && (
            <span className="text-xs text-neutral-400 tabular-nums">{value.toFixed(0)}</span>
          )}
        </div>
      )}
      <div
        className={clsx(
          'w-full rounded-full overflow-hidden',
          size === 'sm' ? 'h-2 bg-neutral-800' : 'h-3 bg-neutral-800 border border-neutral-700',
        )}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label ?? 'Progreso'}
      >
        <div
          className={clsx(
            'h-full rounded-full transition-all duration-700 ease-out',
            variant === 'brand'
              ? 'bg-gradient-to-r from-brand-600 to-brand-400'
              : rank
              ? rankBarColor[rank]
              : 'bg-brand-500',
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
