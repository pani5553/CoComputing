import { useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'
import { clsx } from 'clsx'
import { getJob } from '../api/compute'
import { useJobStore } from '../store/jobStore'
import type { JobStatus } from '../types/compute'
import Card from '../components/ui/Card'
import ProgressBar from '../components/ui/ProgressBar'
import ErrorAlert from '../components/ui/ErrorAlert'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import Button from '../components/ui/Button'
import { formatDateTime, formatCC } from '../utils/format'

// ─── Badge de estado ─────────────────────────────────────────────────────────

const statusConfig: Record<JobStatus, { label: string; classes: string; pulse?: boolean }> = {
  pending: {
    label: 'Pendiente',
    classes: 'text-neutral-400 bg-neutral-400/10 border-neutral-600',
  },
  splitting: {
    label: 'Dividiendo en chunks',
    classes: 'text-info-400 bg-info-400/10 border-info-600',
    pulse: true,
  },
  processing: {
    label: 'Procesando',
    classes: 'text-brand-400 bg-brand-400/10 border-brand-600',
    pulse: true,
  },
  validating: {
    label: 'Validando resultados',
    classes: 'text-warning-400 bg-warning-400/10 border-warning-600',
    pulse: true,
  },
  completed: {
    label: 'Completado',
    classes: 'text-success-500 bg-success-500/10 border-success-600',
  },
  failed: {
    label: 'Fallido',
    classes: 'text-danger-500 bg-danger-500/10 border-danger-600',
  },
}

function JobStatusBadge({ status }: { status: JobStatus }) {
  const cfg = statusConfig[status]
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold border',
        cfg.classes,
      )}
    >
      {cfg.pulse && (
        <span className="relative flex h-2 w-2" aria-hidden="true">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-current" />
        </span>
      )}
      {cfg.label}
    </span>
  )
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const IN_FLIGHT: JobStatus[] = ['pending', 'splitting', 'processing', 'validating']

function isInFlight(status: JobStatus): boolean {
  return IN_FLIGHT.includes(status)
}

// ─── Página ───────────────────────────────────────────────────────────────────

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { currentJob, loading, error, fetchJob, clearError } = useJobStore()

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const jobId = id ?? ''

  const refresh = useCallback(async () => {
    if (!jobId) return
    try {
      const job = await getJob(jobId)
      useJobStore.setState({ currentJob: job })
      // Detener polling cuando llegue a estado terminal
      if (!isInFlight(job.status)) {
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
        }
      }
    } catch {
      // No mostrar error en polling silencioso
    }
  }, [jobId])

  useEffect(() => {
    if (!jobId) return
    fetchJob(jobId)
  }, [jobId, fetchJob])

  // Arrancar polling cuando hay job en vuelo
  useEffect(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    if (currentJob && isInFlight(currentJob.status)) {
      pollingRef.current = setInterval(refresh, 3000)
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [currentJob, refresh])

  // ── Carga inicial ────────────────────────────────────────────────────────────
  if (loading && !currentJob) {
    return (
      <div className="animate-fade-in max-w-3xl">
        <Card variant="default" padding="lg">
          <div className="flex flex-col items-center justify-center min-h-[300px] gap-4">
            <LoadingSpinner size="lg" className="text-brand-400" />
            <p className="text-neutral-500 text-sm animate-pulse">Cargando detalles del trabajo...</p>
          </div>
        </Card>
      </div>
    )
  }

  if (error && !currentJob) {
    return (
      <div className="animate-fade-in max-w-3xl space-y-4">
        <button
          onClick={() => navigate('/jobs')}
          className="flex items-center gap-1.5 text-sm text-neutral-400 hover:text-neutral-200 transition-colors"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          Volver a mis trabajos
        </button>
        <ErrorAlert
          message={error}
          onRetry={() => { clearError(); fetchJob(jobId) }}
        />
      </div>
    )
  }

  if (!currentJob) return null

  const params = currentJob.params as Record<string, unknown>
  const operation = typeof params.operation === 'string' ? params.operation : '—'
  const columns = Array.isArray(params.columns) ? (params.columns as string[]).join(', ') : '—'

  return (
    <div className="animate-fade-in max-w-3xl space-y-6">
      {/* Volver */}
      <button
        onClick={() => navigate('/jobs')}
        className="flex items-center gap-1.5 text-sm text-neutral-400 hover:text-neutral-200 transition-colors"
      >
        <ArrowLeftIcon className="h-4 w-4" />
        Volver a mis trabajos
      </button>

      {/* Cabecera */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-neutral-100 capitalize">
            {currentJob.job_type} · {operation}
          </h1>
          <p className="text-sm text-neutral-500 mt-1">
            Creado: {formatDateTime(currentJob.created_at)}
          </p>
        </div>
        <JobStatusBadge status={currentJob.status} />
      </div>

      {/* Banner completado */}
      {currentJob.status === 'completed' && (
        <div className="flex items-start gap-3 p-4 rounded-lg bg-success-900/40 border border-success-500/50">
          <CheckCircleIcon className="h-6 w-6 text-success-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-success-300">Trabajo completado con exito</p>
            {currentJob.completed_at && (
              <p className="text-xs text-success-500 mt-0.5">
                {formatDateTime(currentJob.completed_at)}
              </p>
            )}
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={() => navigate(`/jobs/${currentJob.id}/result`)}
          >
            Ver resultado
          </Button>
        </div>
      )}

      {/* Banner fallido */}
      {currentJob.status === 'failed' && (
        <div className="flex items-start gap-3 p-4 rounded-lg bg-danger-900/40 border border-danger-500/50">
          <ExclamationCircleIcon className="h-6 w-6 text-danger-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <p className="text-sm font-semibold text-danger-300">El trabajo ha fallado</p>
            <p className="text-xs text-danger-500 mt-0.5">
              Algunos chunks no pudieron validarse. Puedes intentar crear un nuevo trabajo.
            </p>
          </div>
        </div>
      )}

      {/* Progreso */}
      <Card variant="default" padding="lg" className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-neutral-400 uppercase tracking-wide">
            Progreso
          </h2>
          {isInFlight(currentJob.status) && (
            <div className="flex items-center gap-2 text-xs text-neutral-500">
              <LoadingSpinner size="xs" className="text-neutral-500" />
              Actualizando cada 3s
            </div>
          )}
        </div>

        <div
          className="text-5xl font-bold text-neutral-100 tabular-nums text-center py-4"
          role="status"
          aria-live="polite"
        >
          {currentJob.progress.toFixed(1)}%
        </div>

        <ProgressBar value={currentJob.progress} size="md" />

        <p className="text-sm text-neutral-400 text-center">
          <span className="font-semibold text-neutral-200">{currentJob.completed_chunks}</span>
          {' de '}
          <span className="font-semibold text-neutral-200">{currentJob.total_chunks}</span>
          {' chunks completados'}
        </p>
      </Card>

      {/* Detalles */}
      <Card variant="default" padding="lg">
        <h2 className="text-sm font-semibold text-neutral-400 uppercase tracking-wide mb-4">
          Detalles del trabajo
        </h2>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
          <div>
            <dt className="text-xs text-neutral-500 uppercase tracking-wide font-medium">Tipo</dt>
            <dd className="text-sm text-neutral-200 mt-0.5 capitalize">{currentJob.job_type}</dd>
          </div>
          <div>
            <dt className="text-xs text-neutral-500 uppercase tracking-wide font-medium">Operacion</dt>
            <dd className="text-sm text-neutral-200 mt-0.5 capitalize">{operation}</dd>
          </div>
          <div>
            <dt className="text-xs text-neutral-500 uppercase tracking-wide font-medium">Columnas</dt>
            <dd className="text-sm text-neutral-200 mt-0.5 font-mono">{columns}</dd>
          </div>
          <div>
            <dt className="text-xs text-neutral-500 uppercase tracking-wide font-medium">Recompensa total</dt>
            <dd className="text-sm text-success-400 mt-0.5 font-semibold tabular-nums">
              {formatCC(currentJob.reward_total)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-neutral-500 uppercase tracking-wide font-medium">Total chunks</dt>
            <dd className="text-sm text-neutral-200 mt-0.5 tabular-nums">{currentJob.total_chunks}</dd>
          </div>
          {currentJob.completed_at && (
            <div>
              <dt className="text-xs text-neutral-500 uppercase tracking-wide font-medium">Completado el</dt>
              <dd className="text-sm text-neutral-200 mt-0.5">{formatDateTime(currentJob.completed_at)}</dd>
            </div>
          )}
          <div>
            <dt className="text-xs text-neutral-500 uppercase tracking-wide font-medium">ID de trabajo</dt>
            <dd className="text-xs text-neutral-500 mt-0.5 font-mono break-all">{currentJob.id}</dd>
          </div>
        </dl>
      </Card>
    </div>
  )
}
