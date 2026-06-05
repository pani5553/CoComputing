import { clsx } from 'clsx'

type Size = 'xs' | 'sm' | 'md' | 'lg'

interface LoadingSpinnerProps {
  size?: Size
  className?: string
}

const sizeMap: Record<Size, string> = {
  xs: 'h-3 w-3',
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-10 w-10',
}

export default function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  return (
    <svg
      className={clsx('animate-spin text-current', sizeMap[size], className)}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
      <span className="sr-only">Cargando...</span>
    </svg>
  )
}

/** Spinner centrado de página completa */
export function PageSpinner({ label = 'Cargando...' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
      <LoadingSpinner size="lg" className="text-brand-400" />
      <p className="text-neutral-500 text-sm animate-pulse">{label}</p>
    </div>
  )
}
