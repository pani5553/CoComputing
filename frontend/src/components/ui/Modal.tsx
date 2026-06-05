import { useEffect, useRef, type ReactNode } from 'react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { clsx } from 'clsx'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: ReactNode
  size?: 'sm' | 'md' | 'lg'
}

const sizeMap = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
}

export default function Modal({ isOpen, onClose, title, children, size = 'md' }: ModalProps) {
  const titleId = `modal-title-${title.toLowerCase().replace(/\s+/g, '-')}`
  const dialogRef = useRef<HTMLDivElement>(null)

  // Cerrar con Escape
  useEffect(() => {
    if (!isOpen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  // Bloquear scroll del body
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <div
        ref={dialogRef}
        className={clsx(
          'relative w-full rounded-xl',
          'bg-neutral-900 border border-neutral-700',
          'shadow-xl shadow-black/40 p-6',
          'animate-fade-in',
          sizeMap[size],
        )}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 id={titleId} className="text-lg font-semibold text-neutral-100">
            {title}
          </h2>
          <button
            onClick={onClose}
            className="text-neutral-500 hover:text-neutral-300 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 rounded"
            aria-label="Cerrar modal"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {children}
      </div>
    </div>
  )
}
