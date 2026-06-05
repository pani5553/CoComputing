import { ExclamationCircleIcon } from '@heroicons/react/24/outline'

interface ErrorAlertProps {
  message: string
  onRetry?: () => void
  className?: string
}

export default function ErrorAlert({ message, onRetry, className }: ErrorAlertProps) {
  return (
    <div
      className={`flex items-start gap-3 p-4 rounded-lg bg-danger-900/50 border border-danger-500/30 text-danger-300 text-sm ${className ?? ''}`}
      role="alert"
    >
      <ExclamationCircleIcon
        className="h-5 w-5 text-danger-400 flex-shrink-0 mt-0.5"
        aria-hidden="true"
      />
      <div className="flex-1 min-w-0">
        <p>{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-2 text-xs text-danger-400 underline underline-offset-2 hover:text-danger-300 focus:outline-none"
          >
            Reintentar
          </button>
        )}
      </div>
    </div>
  )
}

interface InfoAlertProps {
  message: string
  className?: string
}

export function InfoAlert({ message, className }: InfoAlertProps) {
  return (
    <div
      className={`flex items-start gap-3 p-4 rounded-lg bg-info-900/50 border border-info-500/30 text-info-300 text-sm ${className ?? ''}`}
      role="status"
    >
      <svg className="h-5 w-5 text-info-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p>{message}</p>
    </div>
  )
}

export function SuccessAlert({ message, className }: InfoAlertProps) {
  return (
    <div
      className={`flex items-start gap-3 p-4 rounded-lg bg-success-900/50 border border-success-500/30 text-success-300 text-sm ${className ?? ''}`}
      role="status"
    >
      <svg className="h-5 w-5 text-success-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p>{message}</p>
    </div>
  )
}
