import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { clsx } from 'clsx'
import LoadingSpinner from './LoadingSpinner'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  leftIcon?: ReactNode
  children: ReactNode
}

const variantClasses: Record<Variant, string> = {
  primary: [
    'bg-brand-600 hover:bg-brand-500 active:bg-brand-700',
    'text-white font-semibold',
    'focus:ring-brand-500 focus:ring-offset-neutral-900',
    'hover:shadow-lg hover:shadow-brand-500/20',
  ].join(' '),
  secondary: [
    'bg-neutral-800 hover:bg-neutral-700 active:bg-neutral-900',
    'border border-neutral-700 hover:border-neutral-500',
    'text-neutral-300 hover:text-neutral-100 font-semibold',
    'focus:ring-neutral-500 focus:ring-offset-neutral-900',
  ].join(' '),
  danger: [
    'bg-danger-500/10 hover:bg-danger-500/20',
    'border border-danger-500/50 hover:border-danger-500',
    'text-danger-500 hover:text-danger-400 font-semibold',
    'focus:ring-danger-500 focus:ring-offset-neutral-900',
  ].join(' '),
  ghost: [
    'text-brand-400 hover:text-brand-300',
    'font-medium underline-offset-2 hover:underline',
    'focus:ring-brand-500 focus:ring-offset-neutral-900',
  ].join(' '),
}

const sizeClasses: Record<Size, string> = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-5 py-2.5 text-sm',
  lg: 'px-6 py-3 text-base',
}

export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  leftIcon,
  children,
  className,
  disabled,
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading

  return (
    <button
      {...props}
      disabled={isDisabled}
      className={clsx(
        'inline-flex items-center justify-center gap-2 rounded-lg',
        'transition-all duration-150',
        'focus:outline-none focus:ring-2 focus:ring-offset-2',
        variant !== 'ghost' && sizeClasses[size],
        variantClasses[variant],
        isDisabled && 'opacity-50 cursor-not-allowed',
        loading && 'cursor-wait',
        className,
      )}
    >
      {loading ? (
        <LoadingSpinner size="sm" />
      ) : leftIcon ? (
        <span aria-hidden="true">{leftIcon}</span>
      ) : null}
      {children}
    </button>
  )
}
