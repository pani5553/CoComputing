import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  WifiIcon,
} from '@heroicons/react/24/outline'
import { completeTask, failTask } from '../api/tasks'
import { extractErrorMessage } from '../api/client'
import { useProgress } from '../hooks/useProgress'
import LoadingSpinner, { PageSpinner } from '../components/ui/LoadingSpinner'
import ProgressBar from '../components/ui/ProgressBar'
import Stepper from '../components/ui/Stepper'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import ErrorAlert from '../components/ui/ErrorAlert'
import { AssignmentStatusBadge } from '../components/ui/Badge'
import { formatDateTime } from '../utils/format'

export default function ProcessingPage() {
  const { assignmentId } = useParams<{ assignmentId: string }>()
  const navigate = useNavigate()

  const { progress, loading, error, consecutiveErrors, refetch } = useProgress(assignmentId)

  const [showCompleteModal, setShowCompleteModal] = useState(false)
  const [showFailModal, setShowFailModal] = useState(false)
  const [completing, setCompleting] = useState(false)
  const [failing, setFailing] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  async function handleComplete() {
    if (!progress) return
    setActionError(null)
    setCompleting(true)
    try {
      await completeTask(progress.task_id)
      setShowCompleteModal(false)
      navigate('/dashboard', {
        replace: true,
        state: {
          taskCompleted: true,
          assignmentId,
        },
      })
    } catch (err) {
      setActionError(extractErrorMessage(err))
      setCompleting(false)
    }
  }

  async function handleFail() {
    if (!progress) return
    setActionError(null)
    setFailing(true)
    try {
      await failTask(progress.task_id)
      setShowFailModal(false)
      navigate('/dashboard', {
        replace: true,
        state: {
          taskFailed: true,
          assignmentId,
        },
      })
    } catch (err) {
      setActionError(extractErrorMessage(err))
      setFailing(false)
    }
  }

  // Carga inicial
  if (loading && !progress) {
    return (
      <div className="animate-fade-in max-w-4xl">
        <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-12">
          <div className="space-y-3 mb-8">
            <div className="h-6 bg-neutral-700 rounded w-2/3 animate-pulse" />
            <div className="h-4 bg-neutral-700 rounded w-1/3 animate-pulse" />
          </div>
          <PageSpinner label="Cargando estado de la tarea..." />
        </div>
      </div>
    )
  }

  if (!progress && !loading) {
    return (
      <div className="animate-fade-in max-w-4xl">
        <ErrorAlert
          message={error ?? 'No se pudo cargar el progreso de esta tarea.'}
          onRetry={refetch}
        />
      </div>
    )
  }

  const pct = progress?.progress ?? 0
  const canComplete = progress?.can_complete ?? false
  const stages = progress?.stages ?? []
  const currentStageIndex = progress?.current_stage_index ?? 0

  return (
    <div className="animate-fade-in max-w-4xl space-y-6">
      {/* Cabecera de tarea */}
      <div className="bg-neutral-900 border border-brand-500/30 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-3">
          {progress?.status && (
            <AssignmentStatusBadge status={progress.status} />
          )}
        </div>
        <h1 className="text-2xl font-bold text-neutral-100 leading-tight mb-1">
          {progress?.task_title ?? 'Cargando...'}
        </h1>
        <p className="text-sm text-neutral-500">
          ID de asignación:{' '}
          <span className="font-mono text-neutral-400">{assignmentId}</span>
        </p>
      </div>

      {/* Banner de error de conexión (sin detener polling) */}
      {consecutiveErrors >= 3 && error && (
        <div className="flex items-start gap-3 p-4 rounded-lg bg-info-900/50 border border-info-500/30 text-info-300 text-sm" role="status">
          <WifiIcon className="h-5 w-5 text-info-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <p>No se puede actualizar el progreso. Comprobando la conexión...</p>
            <p className="text-xs text-info-400/70 mt-1">Los datos mostrados corresponden al último valor conocido.</p>
          </div>
        </div>
      )}

      {/* Progreso + Stepper */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Progreso (col-span-2) */}
        <div className="lg:col-span-2 bg-neutral-900 border border-neutral-700 rounded-xl p-6 space-y-5">
          <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">
            Progreso actual
          </h2>
          <div className="border-t border-neutral-700 pt-5">
            {/* Porcentaje grande */}
            <p
              className="text-4xl font-bold text-neutral-100 tabular-nums text-center mb-4"
              role="status"
              aria-live="polite"
            >
              {pct.toFixed(1)}%
            </p>

            {/* Barra */}
            <ProgressBar value={pct} size="md" />

            {/* Meta info */}
            <div className="flex items-center justify-between mt-3">
              <p className="text-xs text-neutral-500">
                {progress?.started_at
                  ? `Iniciado: ${formatDateTime(progress.started_at)}`
                  : 'Aún no iniciado'}
              </p>
              <div className="flex items-center gap-1.5 text-xs text-neutral-600">
                <LoadingSpinner size="xs" className="text-neutral-600" />
                <span>Actualizando cada 3s</span>
              </div>
            </div>
          </div>

          <div className="border-t border-neutral-700 pt-4">
            {canComplete ? (
              <p className="text-xs text-neutral-400 italic">
                La tarea está casi lista. Pulsa "Completar" cuando confirmes que el procesamiento ha terminado.
              </p>
            ) : (
              <p className="text-xs text-neutral-600 italic">
                El botón "Completar" se habilitará cuando el progreso alcance el 80%.
              </p>
            )}
          </div>
        </div>

        {/* Stepper (col-span-1) */}
        <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-6">
          <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-4">
            Etapas
          </h2>
          <div className="border-t border-neutral-700 pt-4">
            {stages.length > 0 ? (
              <Stepper
                stages={stages}
                currentStageIndex={currentStageIndex}
                progress={pct}
              />
            ) : (
              <p className="text-sm text-neutral-500">Sin etapas registradas.</p>
            )}
          </div>
        </div>
      </div>

      {/* Error de acción */}
      {actionError && <ErrorAlert message={actionError} />}

      {/* Botones de acción */}
      <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-6">
        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="primary"
            disabled={!canComplete || completing || failing}
            loading={completing}
            onClick={() => setShowCompleteModal(true)}
            leftIcon={canComplete ? <CheckCircleIcon className="h-4 w-4" /> : undefined}
          >
            {completing ? 'Completando...' : 'Completar tarea'}
          </Button>

          <Button
            variant="danger"
            disabled={completing || failing}
            loading={failing}
            onClick={() => setShowFailModal(true)}
          >
            Reportar problema
          </Button>
        </div>

        {!canComplete && (
          <p className="text-xs text-neutral-600 mt-3">
            El botón "Completar tarea" se activará cuando el progreso alcance el 80%.
            Progreso actual: <span className="tabular-nums">{pct.toFixed(1)}%</span>
          </p>
        )}
      </div>

      {/* Modal: Confirmar completar */}
      <Modal
        isOpen={showCompleteModal}
        onClose={() => !completing && setShowCompleteModal(false)}
        title="Completar tarea"
      >
        <div className="space-y-4">
          <div className="flex flex-col items-center text-center gap-3 py-2">
            <CheckCircleIcon className="h-10 w-10 text-success-400" aria-hidden="true" />
            <div>
              <h3 className="text-base font-semibold text-neutral-100">¿Completar esta tarea?</h3>
              <p className="text-sm text-neutral-400 mt-1">
                Confirmas que el procesamiento ha finalizado correctamente.
              </p>
            </div>
          </div>

          <div className="border-t border-neutral-700 pt-4 flex justify-end gap-3">
            <Button
              variant="secondary"
              disabled={completing}
              onClick={() => setShowCompleteModal(false)}
            >
              Cancelar
            </Button>
            <Button
              variant="primary"
              loading={completing}
              onClick={handleComplete}
            >
              Confirmar y cobrar
            </Button>
          </div>
        </div>
      </Modal>

      {/* Modal: Reportar problema */}
      <Modal
        isOpen={showFailModal}
        onClose={() => !failing && setShowFailModal(false)}
        title="Reportar problema"
      >
        <div className="space-y-4">
          <div className="flex flex-col items-center text-center gap-3 py-2">
            <ExclamationTriangleIcon className="h-10 w-10 text-warning-500" aria-hidden="true" />
            <div>
              <h3 className="text-base font-semibold text-neutral-100">
                ¿Reportar que no puedes completar esta tarea?
              </h3>
              <p className="text-sm text-neutral-400 mt-1">
                Esta acción registra que no has podido finalizar el procesamiento. No recibirás
                la recompensa y tu Trust Score puede verse afectado.
              </p>
            </div>
          </div>

          <div className="border-t border-neutral-700 pt-4 flex justify-end gap-3">
            <Button
              variant="secondary"
              disabled={failing}
              onClick={() => setShowFailModal(false)}
            >
              Cancelar
            </Button>
            <Button
              variant="danger"
              loading={failing}
              onClick={handleFail}
            >
              Reportar problema
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
