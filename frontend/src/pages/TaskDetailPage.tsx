import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ChevronLeftIcon,
  ClockIcon,
  UserGroupIcon,
  CpuChipIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import { getTask, acceptTask, startTask } from '../api/tasks'
import { extractErrorMessage } from '../api/client'
import type { Task } from '../types'
import SkeletonCard from '../components/ui/SkeletonCard'
import ErrorAlert from '../components/ui/ErrorAlert'
import { SuccessAlert } from '../components/ui/ErrorAlert'
import Button from '../components/ui/Button'
import { DifficultyBadge, HardwareBadge, TaskTypeBadge } from '../components/ui/Badge'
import { formatCC } from '../utils/format'

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [task, setTask] = useState<Task | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [acceptLoading, setAcceptLoading] = useState(false)
  const [startLoading, setStartLoading] = useState(false)
  const [accepted, setAccepted] = useState(false)

  async function fetchTask() {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const data = await getTask(id)
      setTask(data)
      // Si ya tenía asignación activa
      if (
        data.active_assignment &&
        (data.active_assignment.status === 'aceptada' ||
          data.active_assignment.status === 'procesando')
      ) {
        setAccepted(true)
      }
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTask()
  }, [id])

  async function handleAccept() {
    if (!task) return
    setActionError(null)
    setAcceptLoading(true)
    try {
      await acceptTask(task.id)
      setAccepted(true)
      // Refrescar la tarea para obtener active_assignment
      const updated = await getTask(task.id)
      setTask(updated)
    } catch (err) {
      setActionError(extractErrorMessage(err))
    } finally {
      setAcceptLoading(false)
    }
  }

  async function handleStart() {
    if (!task) return
    setActionError(null)
    setStartLoading(true)
    try {
      const res = await startTask(task.id)
      navigate(`/procesando/${res.assignment_id}`)
    } catch (err) {
      setActionError(extractErrorMessage(err))
      setStartLoading(false)
    }
  }

  function handleContinue() {
    if (!task?.active_assignment) return
    const assignmentId = task.active_assignment.id
    navigate(`/procesando/${assignmentId}`)
  }

  if (loading) {
    return (
      <div className="animate-fade-in max-w-4xl space-y-4">
        <div className="h-5 w-28 bg-neutral-800 rounded animate-pulse" />
        <SkeletonCard lines={8} />
      </div>
    )
  }

  if (error || !task) {
    return (
      <div className="animate-fade-in max-w-4xl">
        <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-12 flex flex-col items-center gap-4 text-center">
          <ExclamationTriangleIcon className="h-12 w-12 text-neutral-600" aria-hidden="true" />
          <h2 className="text-lg font-semibold text-neutral-300">Tarea no encontrada</h2>
          <p className="text-sm text-neutral-500">Esta tarea no existe o ya no está disponible.</p>
          {error && <p className="text-xs text-danger-400">{error}</p>}
          <Button variant="secondary" onClick={() => navigate('/tareas')}>
            ← Ver todas las tareas
          </Button>
        </div>
      </div>
    )
  }

  const isProcessing = task.active_assignment?.status === 'procesando'
  const isAccepted = task.active_assignment?.status === 'aceptada'
  const hasActiveAssignment = isProcessing || isAccepted || accepted
  const noSlots = task.slots_left === 0 && !hasActiveAssignment
  const slotsPercent = ((task.total_slots - task.slots_left) / task.total_slots) * 100

  return (
    <div className="animate-fade-in max-w-4xl space-y-6">
      {/* Breadcrumb */}
      <Link
        to="/tareas"
        className="inline-flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-300 transition-colors"
      >
        <ChevronLeftIcon className="h-4 w-4" aria-hidden="true" />
        Volver al listado
      </Link>

      {/* Cabecera de tarea */}
      <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-6">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <TaskTypeBadge type={task.task_type} />
          <DifficultyBadge difficulty={task.difficulty} />
          <HardwareBadge hardware={task.hardware_required} />
        </div>
        <h1 className="text-2xl font-bold text-neutral-100 leading-tight mb-2">
          {task.title}
        </h1>
        <p className="text-sm text-neutral-400">
          Solicitante: {task.requester_name}
        </p>
      </div>

      {/* Cuerpo: descripción + detalles */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Descripción (col-span-2) */}
        <div className="lg:col-span-2 bg-neutral-900 border border-neutral-700 rounded-xl p-6">
          <h2 className="text-base font-semibold text-neutral-300 uppercase tracking-wide text-xs mb-3">
            Descripción
          </h2>
          <div className="border-t border-neutral-700 pt-4">
            <p className="text-sm text-neutral-300 leading-relaxed">{task.description}</p>
          </div>
        </div>

        {/* Detalles (col-span-1) */}
        <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-6 space-y-4">
          <h2 className="text-xs font-semibold text-neutral-300 uppercase tracking-wide">
            Detalles
          </h2>
          <div className="border-t border-neutral-700 pt-4 space-y-4">
            {/* Recompensa */}
            <div>
              <p className="text-xs text-neutral-500 uppercase tracking-wide mb-1">Recompensa</p>
              <p className="text-2xl font-bold text-success-400 tabular-nums">
                {formatCC(task.reward)}
              </p>
            </div>

            <div className="border-t border-neutral-800" />

            {/* Duración */}
            <div className="flex items-center gap-2">
              <ClockIcon className="h-4 w-4 text-neutral-500 flex-shrink-0" aria-hidden="true" />
              <div>
                <p className="text-xs text-neutral-500">Duración estimada</p>
                <p className="text-sm font-medium text-neutral-300">
                  {task.duration_min}–{task.duration_max} minutos
                </p>
              </div>
            </div>

            {/* Plazas */}
            <div className="flex items-start gap-2">
              <UserGroupIcon className="h-4 w-4 text-neutral-500 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div className="flex-1">
                <p className="text-xs text-neutral-500">Plazas</p>
                <p className="text-sm font-medium text-neutral-300 mb-1">
                  {task.slots_left} de {task.total_slots} disponibles
                </p>
                <div className="w-full h-1.5 bg-neutral-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-600 rounded-full"
                    style={{ width: `${slotsPercent}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Hardware */}
            <div className="flex items-center gap-2">
              <CpuChipIcon className="h-4 w-4 text-neutral-500 flex-shrink-0" aria-hidden="true" />
              <div>
                <p className="text-xs text-neutral-500">Hardware requerido</p>
                <p className="text-sm font-medium text-neutral-300 capitalize">
                  {task.hardware_required === 'cpu'
                    ? 'CPU'
                    : task.hardware_required === 'gpu'
                    ? 'GPU'
                    : 'CPU + GPU (Mixto)'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Etapas */}
      <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-6">
        <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
          Etapas de procesamiento
        </h2>
        <div className="flex flex-wrap gap-2">
          {task.stages.map((stage, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-neutral-800 border border-neutral-700 text-xs text-neutral-400"
            >
              <span className="text-neutral-600 font-mono">{i + 1}.</span>
              {stage}
            </span>
          ))}
        </div>
      </div>

      {/* Alertas de acción */}
      {actionError && (
        <ErrorAlert message={actionError} />
      )}

      {accepted && !isProcessing && (
        <SuccessAlert message="¡Tarea aceptada correctamente! Ahora puedes iniciar el procesamiento." />
      )}

      {/* Botones de acción */}
      <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-6">
        <div className="flex flex-wrap gap-3 items-center">
          {isProcessing ? (
            <Button
              variant="primary"
              onClick={handleContinue}
            >
              Continuar procesamiento
            </Button>
          ) : isAccepted || accepted ? (
            <>
              <Button
                variant="primary"
                loading={startLoading}
                onClick={handleStart}
              >
                {startLoading ? 'Iniciando...' : 'Iniciar procesamiento'}
              </Button>
              <Button variant="secondary" onClick={() => navigate('/tareas')}>
                Volver al listado
              </Button>
            </>
          ) : noSlots ? (
            <div className="space-y-2">
              <Button variant="primary" disabled>
                Sin plazas disponibles
              </Button>
              <p className="text-xs text-warning-500">
                Esta tarea ya no tiene plazas disponibles.
              </p>
            </div>
          ) : (
            <Button
              variant="primary"
              loading={acceptLoading}
              onClick={handleAccept}
            >
              {acceptLoading ? 'Aceptando...' : 'Aceptar tarea'}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
