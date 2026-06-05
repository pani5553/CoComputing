import { CheckIcon } from '@heroicons/react/24/solid'
import { clsx } from 'clsx'

interface StepperProps {
  stages: string[]
  currentStageIndex: number
  progress: number
}

export default function Stepper({ stages, currentStageIndex, progress }: StepperProps) {
  return (
    <ol className="relative space-y-0">
      {stages.map((stage, idx) => {
        const isCompleted = idx < currentStageIndex || progress >= 100
        const isActive = idx === currentStageIndex && progress < 100
        const isPending = idx > currentStageIndex && progress < 100

        return (
          <li key={idx} className="relative flex gap-4 pb-6 last:pb-0">
            {/* Línea conectora */}
            {idx < stages.length - 1 && (
              <span
                className={clsx(
                  'absolute left-4 top-8 w-0.5 h-full',
                  isCompleted
                    ? idx + 1 < currentStageIndex
                      ? 'bg-success-500/50'
                      : 'bg-gradient-to-b from-success-500/50 to-brand-500/50'
                    : 'bg-neutral-700',
                )}
                aria-hidden="true"
              />
            )}

            {/* Nodo */}
            <div className="flex-shrink-0 relative z-10">
              {isCompleted ? (
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-success-500/20 border-2 border-success-500">
                  <CheckIcon className="h-4 w-4 text-success-500" aria-hidden="true" />
                </span>
              ) : isActive ? (
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-500/20 border-2 border-brand-500 relative">
                  <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-brand-400 opacity-75" aria-hidden="true" />
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-brand-500" />
                </span>
              ) : (
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-800 border-2 border-neutral-600">
                  <span className="text-xs text-neutral-500 font-mono">{idx + 1}</span>
                </span>
              )}
            </div>

            {/* Texto */}
            <div className="flex items-center min-h-[32px]">
              <span
                className={clsx(
                  'text-sm leading-tight',
                  isCompleted && 'text-neutral-400',
                  isActive && 'text-neutral-100 font-semibold',
                  isPending && 'text-neutral-600',
                )}
              >
                {stage}
              </span>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
