import { useEffect, useRef, useCallback } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import {
  BriefcaseIcon,
  PlusIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import { clsx } from 'clsx'
import { useJobStore } from '../store/jobStore'
import type { Job, JobStatus } from '../types/compute'
import Card from '../components/ui/Card'
import ProgressBar from '../components/ui/ProgressBar'
import EmptyState from '../components/ui/EmptyState'
import ErrorAlert from '../components/ui/ErrorAlert'
import SkeletonCard from '../components/ui/SkeletonCard'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import Button from '../components/ui/Button'
import { formatDateTime } from '../utils/format'

// ─── Badge de estado de Job ───────────────────────────────────────────────────

const jobStatusConfig: Record<
  JobStatus,
  { label: string; classes: string; pulse?: boolean }
> = {
  pending: {
    label: 'Pendiente',
    classes: 'text-neutral-400 bg-neutral-400/10 border-neutral-600',
  },
  splitting: {
    label: 'Dividiendo',
    classes: 'text-info-400 bg-info-400/10 border-info-600',
    pulse: true,
  },
  processing: {
    label: 'Procesando',
    classes: 'text-brand-400 bg-brand-400/10 border-brand-600',
    pulse: true,
  },
  validating: {
    label: 'Validando',
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
  const cfg = jobStatusConfig[status]
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold border',
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

const IN_FLIGHT_STATUSES: JobStatus[] = ['pending', 'splitting', 'processing', 'validating']

function isInFlight(status: JobStatus): boolean {
  return IN_FLIGHT_STATUSES.includes(status)
}

function JobCard({ job }: { job: Job }) {
  const params = job.params as Record<string, unknown>
  const operation = typeof params.operation === 'string' ? params.operation : '—'

  return (
    <Link to={`/jobs/${job.id}`} className="block group">
      <Card
        variant="default"
        padding="md"
        className="hover:border-neutral-600 transition-colors group-focus:ring-2 group-focus:ring-brand-500"
      >
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-neutral-200 truncate capitalize">
              {job.job_type} · {operation}
            </p>
            <p className="text-xs text-neutral-500 mt-0.5">
              {formatDateTime(job.created_at)}
            </p>
          </div>
          <JobStatusBadge status={job.status} />
        </div>

        <ProgressBar
          value={job.progress}
          size="sm"
          label={`${job.completed_chunks} de ${job.total_chunks} chunks`}
          showLabel
        />

        <div className="flex items-center justify-between mt-3">
          <span className="text-xs text-neutral-500">
            Recompensa:{' '}
            <span className="text-neutral-300 font-medium">
              {job.reward_total.toFixed(2)} CC
            </span>
          </span>
          {job.status === 'completed' && (
            <span className="text-xs text-success-400 font-medium">Ver resultado →</span>
          )}
        </div>
      </Card>
    </Link>
  )
}

// ─── Página principal ─────────────────────────────────────────────────────────

export default function JobListPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { jobs, loading, error, fetchJobs, clearError } = useJobStore()

  // Toast desde NewJobPage
  const locationState = location.state as { toast?: string } | null
  const toastMessage = locationState?.toast ?? null

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const hasInFlight = jobs.some((j) => isInFlight(j.status))

  const load = useCallback(() => {
    fetchJobs()
  }, [fetchJobs])

  useEffect(() => {
    load()
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [load])

  // Polling automático cada 5s si hay jobs en vuelo
  useEffect(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    if (hasInFlight) {
      pollingRef.current = setInterval(load, 5000)
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [hasInFlight, load])

  // Limpiar el state de location tras mostrar el toast
  useEffect(() => {
    if (toastMessage) {
      window.history.replaceState({}, '')
    }
  }, [toastMessage])

  return (
    <div className="animate-fade-in space-y-6">
      {/* Cabecera */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-100">Mis trabajos</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Trabajos de cómputo distribuido que has enviado.
          </p>
        </div>
        <Button
          variant="primary"
          size="sm"
          onClick={() => navigate('/jobs/new')}
          leftIcon={<PlusIcon className="h-4 w-4" />}
        >
          Nuevo trabajo
        </Button>
      </div>

      {/* Toast de éxito */}
      {toastMessage && (
        <div
          className="flex items-center gap-3 p-4 rounded-lg bg-success-900/40 border border-success-500/30 text-success-300 text-sm"
          role="status"
        >
          <svg className="h-5 w-5 text-success-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {toastMessage}
        </div>
      )}

      {/* Indicador de polling */}
      {hasInFlight && !loading && (
        <div className="flex items-center gap-2 text-xs text-neutral-500">
          <LoadingSpinner size="xs" className="text-neutral-500" />
          Actualizando automáticamente cada 5 segundos...
        </div>
      )}

      {/* Error */}
      {error && (
        <ErrorAlert
          message={error}
          onRetry={() => { clearError(); load() }}
        />
      )}

      {/* Cargando (skeleton) */}
      {loading && jobs.length === 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} lines={4} />
          ))}
        </div>
      )}

      {/* Estado vacío */}
      {!loading && !error && jobs.length === 0 && (
        <Card variant="default" padding="none">
          <EmptyState
            icon={<BriefcaseIcon className="h-12 w-12" />}
            title="Todavía no has enviado ningún trabajo."
            description="Sube un CSV o usa datos de prueba para ver el cómputo distribuido en acción."
            action={{
              label: 'Crear tu primer trabajo',
              onClick: () => navigate('/jobs/new'),
            }}
          />
        </Card>
      )}

      {/* Lista de jobs */}
      {jobs.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      )}

      {/* Botón manual de refresco */}
      {jobs.length > 0 && !hasInFlight && (
        <div className="flex justify-center pt-2">
          <button
            onClick={load}
            className="flex items-center gap-2 text-xs text-neutral-500 hover:text-neutral-300 transition-colors"
          >
            <ArrowPathIcon className="h-3.5 w-3.5" />
            Actualizar lista
          </button>
        </div>
      )}
    </div>
  )
}
