import type { HTMLAttributes, ReactNode } from 'react'
import { clsx } from 'clsx'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
  variant?: 'default' | 'accent' | 'elite'
  padding?: 'sm' | 'md' | 'lg' | 'none'
}

const paddingMap = {
  none: '',
  sm: 'p-4',
  md: 'p-5',
  lg: 'p-6',
}

export default function Card({
  children,
  variant = 'default',
  padding = 'md',
  className,
  ...props
}: CardProps) {
  return (
    <div
      {...props}
      className={clsx(
        'rounded-xl',
        paddingMap[padding],
        variant === 'default' && 'bg-neutral-900 border border-neutral-700',
        variant === 'accent' && 'bg-neutral-900 border border-brand-500/30 shadow-lg shadow-brand-500/5',
        variant === 'elite' && 'bg-neutral-900 border border-amber-600/50 shadow-lg shadow-amber-500/20',
        className,
      )}
    >
      {children}
    </div>
  )
}
