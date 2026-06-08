import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeftIcon,
  XCircleIcon,
  UserIcon,
  CheckCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline'
import { getClientTaskDetail, cancelTask } from '../../api/clientApi'
import { extractErrorMessage } from '../../api/client'
import type { AssignmentInfo, ClientTaskDetail } from '../../types'
import Button from '../../components/ui/Button'
import ErrorAlert from '../../components/ui/ErrorAlert'
import Modal from '../../components/ui/Modal'
import SkeletonCard from '../../components/ui/SkeletonCard'
import { formatCC, formatDateTime } from '../../utils/format'
import { clsx } from 'clsx'

const ASSIGNMENT_STATUS: Record<string, { label: string; classes: string; icon: typeof ClockIcon }> = {
  aceptada: { label: 'Aceptada', classes: 'text-blue-400 bg-blue-400/10 border-blue-600', icon: ClockIcon },
  procesando: { label: 'Procesando', classes: 'text-brand-400 bg-brand-400/10 border-brand-600', icon: ClockIcon },
  completada: { label: 'Completada', classes: 'text-emerald-400 bg-emerald-400/10 border-emerald-600', icon: CheckCircleIcon },
  fallida: { label: 'Fallida', classes: 'text-red-400 bg-red-400/10 border-red-600', icon: XCircleIcon },
  cancelada: { label: 'Cancelada', classes: 'text-neutral-400 bg-neutral-400/10 border-neutral-600', icon: XCircleIcon },
}

function AssignmentRow({ a }: { a: AssignmentInfo }) {
  const cfg = ASSIGNMENT_STATUS[a.status] ?? ASSIGNMENT_STATUS.aceptada
  const Icon = cfg.icon
  return (
    <div className="flex items-center gap-3 py-3 border-b border-neutral-800 last:border-0">
      <div className="h-8 w-8 rounded-full bg-neutral-800 border border-neutral-700 flex items-center justify-center shrink-0">
        <UserIcon className="h-4 w-4 text-neutral-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-neutral-200 truncate">{a.provider_name}</p>
        <p className="text-xs text-neutral-500">{formatDateTime(a.accepted_at)}</p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {a.reward_paid != null && (
          <span className="text-xs text-emerald-400 font-medium">{formatCC(a.reward_paid)}</span>
        )}
        <span className={clsx('text-xs px-2 py-0.5 rounded border font-semibold uppercase tracking-wide flex items-center gap-1', cfg.classes)}>
          <Icon className="h-3 w-3" />
          {cfg.label}
        </span>
      </div>
    </div>
  )
}

export default function ClientTaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const navigate = useNavigate()

  const [task, setTask] = useState<ClientTaskDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [cancelOpen, setCancelOpen] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [cancelError, setCancelError] = useState<string | null>(null)

  useEffect(() => {
    if (!taskId) return
    setLoading(true)
    getClientTaskDetail(taskId)
      .then(setTask)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [taskId])

  async function handleCancel() {
    if (!taskId) return
    setCancelError(null)
    setCancelling(true)
    try {
      await cancelTask(taskId)
      navigate('/cliente/mis-tareas')
    } catch (err) {
      setCancelError(extractErrorMessage(err))
    } finally {
      setCancelling(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto py-8 px-4 space-y-4">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    )
  }

  if (error || !task) {
    return (
      <div className="max-w-3xl mx-auto py-8 px-4">
        <ErrorAlert message={error ?? 'Tarea no encontrada'} />
        <Button variant="secondary" onClick={() => navigate('/cliente/mis-tareas')} className="mt-4">
          <ArrowLeftIcon className="h-4 w-4 mr-1.5" />
          Volver
        </Button>
      </div>
    )
  }

  const canCancel = task.status === 'disponible' || task.status === 'en_progreso'
  const completedCount = task.assignments.filter((a) => a.status === 'completada').length

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <button
        onClick={() => navigate('/cliente/mis-tareas')}
        className="flex items-center gap-1.5 text-sm text-neutral-400 hover:text-neutral-200 transition-colors mb-6"
      >
        <ArrowLeftIcon className="h-4 w-4" />
        Mis tareas
      </button>

      {/* Header */}
      <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-6 mb-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <h1 className="text-xl font-bold text-neutral-100 mb-1">{task.title}</h1>
            <p className="text-sm text-neutral-500">{task.description}</p>
          </div>
          {canCancel && (
            <Button
              variant="danger"
              onClick={() => setCancelOpen(true)}
              className="shrink-0 flex items-center gap-1.5"
            >
              <XCircleIcon className="h-4 w-4" />
              Cancelar
            </Button>
          )}
        </div>

        <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-4 pt-5 border-t border-neutral-800">
          <div>
            <p className="text-xs text-neutral-500 mb-0.5">Recompensa/plaza</p>
            <p className="text-sm font-semibold text-brand-400">{formatCC(task.reward)}</p>
          </div>
          <div>
            <p className="text-xs text-neutral-500 mb-0.5">Plazas</p>
            <p className="text-sm font-semibold text-neutral-200">{completedCount}/{task.total_slots}</p>
          </div>
          <div>
            <p className="text-xs text-neutral-500 mb-0.5">Escrow retenido</p>
            <p className="text-sm font-semibold text-amber-400">{formatCC(task.escrow_held)}</p>
          </div>
          <div>
            <p className="text-xs text-neutral-500 mb-0.5">Liberado</p>
            <p className="text-sm font-semibold text-emerald-400">{formatCC(task.escrow_released)}</p>
          </div>
        </div>
      </div>

      {/* Assignments */}
      <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-6">
        <h2 className="text-sm font-semibold text-neutral-300 uppercase tracking-wide mb-4">
          Proveedores ({task.assignments.length})
        </h2>

        {task.assignments.length === 0 ? (
          <p className="text-sm text-neutral-500 text-center py-6">
            Aún no hay proveedores asignados a esta tarea.
          </p>
        ) : (
          <div>
            {task.assignments.map((a) => (
              <AssignmentRow key={a.id} a={a} />
            ))}
          </div>
        )}
      </div>

      {/* Cancel modal */}
      <Modal isOpen={cancelOpen} onClose={() => setCancelOpen(false)} title="Cancelar tarea">
        <p className="text-sm text-neutral-300 mb-2">
          ¿Seguro que quieres cancelar <strong className="text-neutral-100">{task.title}</strong>?
        </p>
        <p className="text-sm text-neutral-400 mb-5">
          Se reembolsarán los fondos del escrow de las plazas no completadas ({formatCC(task.escrow_held - task.escrow_released)}).
        </p>
        {cancelError && <ErrorAlert message={cancelError} className="mb-4" />}
        <div className="flex gap-3 justify-end">
          <Button variant="secondary" onClick={() => setCancelOpen(false)}>
            Volver
          </Button>
          <Button variant="danger" loading={cancelling} onClick={handleCancel}>
            Sí, cancelar tarea
          </Button>
        </div>
      </Modal>
    </div>
  )
}
