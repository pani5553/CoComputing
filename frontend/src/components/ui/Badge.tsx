import type { ReactNode } from 'react'
import { clsx } from 'clsx'
import {
  UserIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline'
import {
  BoltIcon as BoltSolid,
  StarIcon as StarSolid,
} from '@heroicons/react/24/solid'
import type { Rank, AssignmentStatus, Difficulty, HardwareRequired } from '../../types'

// ─── Rango ────────────────────────────────────────────────────────────────────

type RankSize = 'sm' | 'md'

interface RankBadgeProps {
  rank: Rank
  size?: RankSize
}

const rankConfig: Record<
  Rank,
  { label: string; classes: string; icon: ReactNode }
> = {
  nuevo: {
    label: 'Nuevo',
    classes: 'text-slate-400 bg-slate-400/10 border-slate-600',
    icon: <UserIcon className="h-3.5 w-3.5" aria-hidden="true" />,
  },
  confiable: {
    label: 'Confiable',
    classes: 'text-blue-400 bg-blue-400/10 border-blue-600',
    icon: <ShieldCheckIcon className="h-3.5 w-3.5" aria-hidden="true" />,
  },
  experto: {
    label: 'Experto',
    classes: 'text-emerald-400 bg-emerald-400/10 border-emerald-600',
    icon: <BoltSolid className="h-3.5 w-3.5" aria-hidden="true" />,
  },
  elite: {
    label: 'Élite',
    classes: 'text-amber-400 bg-amber-400/10 border-amber-600',
    icon: <StarSolid className="h-3.5 w-3.5" aria-hidden="true" />,
  },
}

export function RankBadge({ rank, size = 'sm' }: RankBadgeProps) {
  const cfg = rankConfig[rank]
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded border font-semibold tracking-wide uppercase',
        cfg.classes,
        size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-4 py-2 text-sm',
      )}
    >
      {size === 'md'
        ? rank === 'experto'
          ? <BoltSolid className="h-5 w-5" aria-hidden="true" />
          : rank === 'elite'
          ? <StarSolid className="h-5 w-5" aria-hidden="true" />
          : rank === 'confiable'
          ? <ShieldCheckIcon className="h-5 w-5" aria-hidden="true" />
          : <UserIcon className="h-5 w-5" aria-hidden="true" />
        : cfg.icon}
      {cfg.label}
    </span>
  )
}

// ─── Estado de asignación ─────────────────────────────────────────────────────

interface AssignmentStatusBadgeProps {
  status: AssignmentStatus
}

const statusConfig: Record<
  AssignmentStatus,
  { label: string; classes: string; pulse?: boolean }
> = {
  aceptada: {
    label: 'Aceptada',
    classes: 'text-info-400 bg-info-400/10 border-info-600',
  },
  procesando: {
    label: 'En proceso',
    classes: 'text-brand-400 bg-brand-400/10 border-brand-600',
    pulse: true,
  },
  completada: {
    label: 'Completada',
    classes: 'text-success-500 bg-success-500/10 border-success-600',
  },
  fallida: {
    label: 'Fallida',
    classes: 'text-danger-500 bg-danger-500/10 border-danger-600',
  },
  cancelada: {
    label: 'Cancelada',
    classes: 'text-neutral-500 bg-neutral-500/10 border-neutral-600',
  },
}

export function AssignmentStatusBadge({ status }: AssignmentStatusBadgeProps) {
  const cfg = statusConfig[status]
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold border',
        cfg.classes,
      )}
    >
      {cfg.pulse ? (
        <span className="relative flex h-2 w-2" aria-hidden="true">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-500" />
        </span>
      ) : null}
      {cfg.label}
    </span>
  )
}

// ─── Dificultad ───────────────────────────────────────────────────────────────

interface DifficultyBadgeProps {
  difficulty: Difficulty
}

const difficultyConfig: Record<Difficulty, { label: string; classes: string }> = {
  facil: {
    label: 'Fácil',
    classes: 'text-success-400 bg-success-400/10 border-success-700',
  },
  medio: {
    label: 'Medio',
    classes: 'text-warning-400 bg-warning-400/10 border-warning-700',
  },
  dificil: {
    label: 'Difícil',
    classes: 'text-danger-400 bg-danger-400/10 border-danger-700',
  },
}

export function DifficultyBadge({ difficulty }: DifficultyBadgeProps) {
  const cfg = difficultyConfig[difficulty]
  return (
    <span
      className={clsx(
        'inline-flex items-center px-2.5 py-1 rounded text-xs font-semibold border',
        cfg.classes,
      )}
    >
      {cfg.label}
    </span>
  )
}

// ─── Hardware requerido ───────────────────────────────────────────────────────

import { CpuChipIcon, RectangleGroupIcon, CircleStackIcon } from '@heroicons/react/24/outline'

interface HardwareBadgeProps {
  hardware: HardwareRequired
}

const hardwareConfig: Record<
  HardwareRequired,
  { label: string; classes: string; icon: ReactNode }
> = {
  cpu: {
    label: 'CPU',
    classes: 'text-neutral-300 bg-neutral-700/50 border-neutral-600',
    icon: <CpuChipIcon className="h-3.5 w-3.5" aria-hidden="true" />,
  },
  gpu: {
    label: 'GPU',
    classes: 'text-brand-300 bg-brand-300/10 border-brand-700',
    icon: <RectangleGroupIcon className="h-3.5 w-3.5" aria-hidden="true" />,
  },
  mixto: {
    label: 'Mixto',
    classes: 'text-purple-300 bg-purple-300/10 border-purple-700',
    icon: <CircleStackIcon className="h-3.5 w-3.5" aria-hidden="true" />,
  },
}

export function HardwareBadge({ hardware }: HardwareBadgeProps) {
  const cfg = hardwareConfig[hardware]
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold border',
        cfg.classes,
      )}
    >
      {cfg.icon}
      {cfg.label}
    </span>
  )
}

// ─── Tipo de tarea ────────────────────────────────────────────────────────────

import type { TaskType } from '../../types'

const taskTypeLabels: Record<TaskType, string> = {
  renderizado_3d: 'Renderizado 3D',
  entrenamiento_ml: 'Entrenamiento ML',
  transcodificacion_video: 'Transcodificación',
  analisis_datos: 'Análisis de datos',
  simulacion_fisica: 'Simulación física',
}

export function TaskTypeBadge({ type }: { type: TaskType }) {
  return (
    <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-semibold bg-neutral-700/60 border border-neutral-600 text-neutral-300">
      {taskTypeLabels[type]}
    </span>
  )
}

// ─── Tipo de transacción ──────────────────────────────────────────────────────

import type { TransactionType } from '../../types'

const txTypeConfig: Record<TransactionType, { label: string; classes: string }> = {
  pago_tarea: {
    label: 'Pago de tarea',
    classes: 'text-success-400 bg-success-400/10',
  },
  retiro: {
    label: 'Retiro',
    classes: 'text-info-400 bg-info-400/10',
  },
  bonus: {
    label: 'Bono',
    classes: 'text-amber-400 bg-amber-400/10',
  },
  penalizacion: {
    label: 'Penalización',
    classes: 'text-danger-400 bg-danger-400/10',
  },
}

export function TransactionTypeBadge({ type }: { type: TransactionType }) {
  const cfg = txTypeConfig[type]
  return (
    <span className={clsx('inline-flex px-2 py-0.5 rounded text-xs font-medium', cfg.classes)}>
      {cfg.label}
    </span>
  )
}

// ─── Estado de transacción ────────────────────────────────────────────────────

import type { TransactionStatus } from '../../types'

const txStatusConfig: Record<TransactionStatus, { label: string; classes: string }> = {
  completada: {
    label: 'Completada',
    classes: 'text-success-400',
  },
  pendiente: {
    label: 'Pendiente',
    classes: 'text-warning-400',
  },
  cancelada: {
    label: 'Cancelada',
    classes: 'text-neutral-500',
  },
}

export function TransactionStatusBadge({ status }: { status: TransactionStatus }) {
  const cfg = txStatusConfig[status]
  return (
    <span className={clsx('text-xs font-medium', cfg.classes)}>
      {cfg.label}
    </span>
  )
}
