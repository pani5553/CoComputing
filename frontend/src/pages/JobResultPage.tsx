import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeftIcon,
  ArrowDownTrayIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'
import { getJobResult, getJob } from '../api/compute'
import { extractErrorMessage } from '../api/client'
import type { JobResultResponse } from '../types/compute'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import ErrorAlert from '../components/ui/ErrorAlert'
import { PageSpinner } from '../components/ui/LoadingSpinner'
import { formatDateTime, formatCC } from '../utils/format'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDuration(createdAt: string, completedAt: string): string {
  const diffMs = new Date(completedAt).getTime() - new Date(createdAt).getTime()
  const totalSec = Math.floor(diffMs / 1000)
  if (totalSec < 60) return `${totalSec}s`
  const min = Math.floor(totalSec / 60)
  const sec = totalSec % 60
  return sec > 0 ? `${min}min ${sec}s` : `${min}min`
}

function renderResultValue(value: unknown): string {
  if (typeof value === 'number') return value.toFixed(4)
  if (typeof value === 'object' && value !== null) return JSON.stringify(value)
  return String(value)
}

// ─── Página ───────────────────────────────────────────────────────────────────

export default function JobResultPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const jobId = id ?? ''

  const [result, setResult] = useState<JobResultResponse | null>(null)
  const [jobCreatedAt, setJobCreatedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!jobId) return
    load()
  }, [jobId]) // eslint-disable-line react-hooks/exhaustive-deps

  async function load() {
    setLoading(true)
    setError(null)
    try {
      // Primero verificamos el estado del job; si no está completed, redirigimos
      const job = await getJob(jobId)
      setJobCreatedAt(job.created_at)
      if (job.status !== 'completed') {
        navigate(`/jobs/${jobId}`, { replace: true })
        return
      }
      const res = await getJobResult(jobId)
      setResult(res)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  function handleDownload() {
    if (!result) return
    const blob = new Blob([JSON.stringify(result, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `job-${jobId}-result.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // ── Estados ───────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="animate-fade-in max-w-3xl">
        <PageSpinner label="Cargando resultado..." />
      </div>
    )
  }

  if (error) {
    return (
      <div className="animate-fade-in max-w-3xl space-y-4">
        <button
          onClick={() => navigate(`/jobs/${jobId}`)}
          className="flex items-center gap-1.5 text-sm text-neutral-400 hover:text-neutral-200 transition-colors"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          Volver al detalle
        </button>
        <ErrorAlert message={error} onRetry={load} />
      </div>
    )
  }

  if (!result) return null

  // Extraer datos del resultado
  const resultData = result.result as Record<string, unknown>
  const operation = typeof resultData.operation === 'string' ? resultData.operation : '—'
  const columnsResult = (
    typeof resultData.columns === 'object' && resultData.columns !== null
      ? resultData.columns
      : {}
  ) as Record<string, unknown>

  const tableRows = Object.entries(columnsResult)

  const duration =
    jobCreatedAt && result.completed_at
      ? formatDuration(jobCreatedAt, result.completed_at)
      : '—'

  const rewardTotal = result.total_chunks * 0.1

  return (
    <div className="animate-fade-in max-w-3xl space-y-6">
      {/* Navegación */}
      <button
        onClick={() => navigate(`/jobs/${jobId}`)}
        className="flex items-center gap-1.5 text-sm text-neutral-400 hover:text-neutral-200 transition-colors"
      >
        <ArrowLeftIcon className="h-4 w-4" />
        Volver al detalle
      </button>

      {/* Banner de exito */}
      <div className="flex items-center gap-3 p-4 rounded-lg bg-success-900/40 border border-success-500/50">
        <CheckCircleIcon className="h-6 w-6 text-success-400 flex-shrink-0" aria-hidden="true" />
        <div>
          <p className="text-sm font-semibold text-success-300">Trabajo completado correctamente</p>
          {result.completed_at && (
            <p className="text-xs text-success-500 mt-0.5">
              Completado el {formatDateTime(result.completed_at)}
            </p>
          )}
        </div>
      </div>

      {/* Cabecera + botón descarga */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-neutral-100">
            Resultado del trabajo
          </h1>
          <p className="text-sm text-neutral-500 mt-1 capitalize">
            Operacion: <span className="text-neutral-300 font-medium">{operation}</span>
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={handleDownload}
          leftIcon={<ArrowDownTrayIcon className="h-4 w-4" />}
        >
          Descargar JSON
        </Button>
      </div>

      {/* Tabla de resultados */}
      <Card variant="accent" padding="none">
        <div className="px-5 py-4 border-b border-neutral-700">
          <h2 className="text-sm font-semibold text-neutral-300 uppercase tracking-wide">
            Resultado por columna
          </h2>
        </div>
        {tableRows.length > 0 ? (
          <table className="w-full">
            <thead>
              <tr className="border-b border-neutral-800">
                <th className="px-5 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                  Columna
                </th>
                <th className="px-5 py-3 text-right text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                  Valor ({operation})
                </th>
              </tr>
            </thead>
            <tbody>
              {tableRows.map(([col, val], i) => (
                <tr
                  key={col}
                  className={`${
                    i < tableRows.length - 1 ? 'border-b border-neutral-800' : ''
                  } hover:bg-neutral-800/30 transition-colors`}
                >
                  <td className="px-5 py-3.5 text-sm font-mono text-neutral-300">{col}</td>
                  <td className="px-5 py-3.5 text-sm font-semibold text-neutral-100 tabular-nums text-right">
                    {renderResultValue(val)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="px-5 py-8 text-center text-sm text-neutral-500">
            No hay datos de columnas disponibles en este resultado.
          </div>
        )}
      </Card>

      {/* Metadatos */}
      <Card variant="default" padding="lg">
        <h2 className="text-sm font-semibold text-neutral-400 uppercase tracking-wide mb-4">
          Metadatos del trabajo
        </h2>
        <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <dt className="text-xs text-neutral-500 uppercase tracking-wide font-medium">Operacion</dt>
            <dd className="text-sm text-neutral-200 mt-0.5 capitalize font-semibold">{operation}</dd>
          </div>
          <div>
            <dt className="text-xs text-neutral-500 uppercase tracking-wide font-medium">Chunks procesados</dt>
            <dd className="text-sm text-neutral-200 mt-0.5 font-semibold tabular-nums">
              {result.completed_chunks} / {result.total_chunks}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-neutral-500 uppercase tracking-wide font-medium">Recompensa pagada</dt>
            <dd className="text-sm text-success-400 mt-0.5 font-semibold tabular-nums">
              {formatCC(rewardTotal)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-neutral-500 uppercase tracking-wide font-medium">Duracion total</dt>
            <dd className="text-sm text-neutral-200 mt-0.5 font-semibold tabular-nums">{duration}</dd>
          </div>
        </dl>
      </Card>

      {/* JSON raw expandible */}
      <details className="group">
        <summary className="cursor-pointer text-xs text-neutral-500 hover:text-neutral-300 transition-colors select-none">
          Ver JSON completo
        </summary>
        <Card variant="default" padding="md" className="mt-2 overflow-auto max-h-80">
          <pre className="text-xs text-neutral-400 font-mono whitespace-pre-wrap break-all">
            {JSON.stringify(result, null, 2)}
          </pre>
        </Card>
      </details>
    </div>
  )
}
