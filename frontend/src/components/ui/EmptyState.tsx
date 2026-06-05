import type { ReactNode } from 'react'
import Button from './Button'

interface EmptyStateProps {
  icon: ReactNode
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
  actionVariant?: 'primary' | 'secondary'
}

export default function EmptyState({
  icon,
  title,
  description,
  action,
  actionVariant = 'primary',
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 px-6 text-center">
      <div className="text-neutral-700">{icon}</div>
      <div className="space-y-1">
        <p className="text-neutral-400 font-medium">{title}</p>
        {description && (
          <p className="text-sm text-neutral-600">{description}</p>
        )}
      </div>
      {action && (
        <Button variant={actionVariant} onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  )
}
