import type { InputHTMLAttributes, ReactNode } from 'react'
import { clsx } from 'clsx'
import { ExclamationCircleIcon } from '@heroicons/react/24/outline'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
  suffix?: string
  rightElement?: ReactNode
}

export default function Input({
  label,
  error,
  helperText,
  suffix,
  rightElement,
  id,
  className,
  disabled,
  ...props
}: InputProps) {
  const inputId = id ?? (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined)

  return (
    <div className="w-full">
      {label && (
        <label
          htmlFor={inputId}
          className="block text-sm font-medium text-neutral-300 mb-1.5"
        >
          {label}
        </label>
      )}

      <div className="relative">
        <input
          id={inputId}
          disabled={disabled}
          {...props}
          className={clsx(
            'w-full px-4 py-2.5 rounded-lg',
            'bg-neutral-800 border',
            'text-neutral-100 placeholder:text-neutral-500 text-sm',
            'focus:outline-none focus:ring-1',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'transition-colors duration-150',
            error
              ? 'border-danger-500 focus:border-danger-500 focus:ring-danger-500'
              : 'border-neutral-700 focus:border-brand-500 focus:ring-brand-500',
            suffix && 'pr-12',
            rightElement && 'pr-12',
            className,
          )}
        />

        {suffix && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 text-sm select-none">
            {suffix}
          </span>
        )}

        {rightElement && !suffix && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2">
            {rightElement}
          </span>
        )}
      </div>

      {error && (
        <p className="mt-1.5 text-xs text-danger-500 flex items-center gap-1" role="alert">
          <ExclamationCircleIcon className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />
          {error}
        </p>
      )}

      {helperText && !error && (
        <p className="mt-1.5 text-xs text-neutral-500">{helperText}</p>
      )}
    </div>
  )
}
