import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeftIcon, BriefcaseIcon } from '@heroicons/react/24/outline'
import { getHistory } from '../api/tasks'
import { extractErrorMessage } from '../api/client'
import type { Assignment } from '../types'
import { AssignmentStatusBadge, TaskTypeBadge } from '../components/ui/Badge'
import { SkeletonRow } from '../components/ui/SkeletonCard'
import ErrorAlert from '../components/ui/ErrorAlert'
import Button from '../components/ui/Button'
import EmptyState from '../components/ui/EmptyState'
import { formatCC, formatDate } from '../utils/format'

// El backend (GET /tasks/my/history) devuelve TODAS las asignaciones del
// proveedor de una sola vez, sin paginar. Paginamos aquí en cliente, igual
// que WalletPage hace con su historial de transacciones.
const PAGE_SIZE = 10

export default function TaskHistoryPage() {
  const navigate = useNavigate()
  const [history, setHistory] = useState<Assignment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(0)

  async function loadHistory() {
    setLoading(true)
    setError(null)
    try {
      const data = await getHistory()
      setHistory(data.assignments)
      setPage(0)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadHistory()
  }, [])

  const totalPages = Math.max(1, Math.ceil(history.length / PAGE_SIZE))
  const pageItems = history.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE)

  return (
    <div className="animate-fade-in space-y-6">
      {/* Volver */}
      <button
        onClick={() => navigate('/dashboard')}
        className="flex items-center gap-1.5 text-sm text-neutral-400 hover:text-neutral-200 transition-colors"
      >
        <ArrowLeftIcon className="h-4 w-4" />
        Volver al dashboard
      </button>

      {/* Cabecera */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-neutral-100">Historial de tareas</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Todas las tareas que has aceptado como proveedor, de más reciente a más antigua.
          </p>
        </div>
        {!loading && !error && history.length > 0 && (
          <p className="text-sm text-neutral-500">
            {history.length} {history.length === 1 ? 'tarea procesada' : 'tareas procesadas'}
          </p>
        )}
      </div>

      {/* Error */}
      {error && <ErrorAlert message={error} onRetry={loadHistory} />}

      {/* Cargando (skeleton) */}
      {loading ? (
        <div className="w-full border border-neutral-700 rounded-xl overflow-hidden">
          <table className="w-full">
            <tbody>
              {Array.from({ length: 8 }).map((_, i) => (
                <SkeletonRow key={i} />
              ))}
            </tbody>
          </table>
        </div>
      ) : error ? null : history.length === 0 ? (
        /* Estado vacío */
        <div className="bg-neutral-900 border border-neutral-700 rounded-xl">
          <EmptyState
            icon={<BriefcaseIcon className="h-12 w-12" />}
            title="Aún no has procesado ninguna tarea."
            action={{
              label: 'Explorar tareas disponibles',
              onClick: () => navigate('/tareas'),
            }}
          />
        </div>
      ) : (
        <>
          <div className="w-full border border-neutral-700 rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-neutral-800 border-b border-neutral-700">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                    Tarea
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide hidden sm:table-cell">
                    Tipo
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                    Estado
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                    Recompensa
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide hidden md:table-cell">
                    Aceptada
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide hidden md:table-cell">
                    Completada
                  </th>
                </tr>
              </thead>
              <tbody>
                {pageItems.map((a) => (
                  <tr
                    key={a.id}
                    className="border-b border-neutral-800 last:border-0 hover:bg-neutral-800/50 transition-colors duration-100"
                  >
                    <td className="px-4 py-3.5 text-sm text-neutral-300 max-w-[220px] truncate">
                      {a.task_title ?? '—'}
                    </td>
                    <td className="px-4 py-3.5 hidden sm:table-cell">
                      {a.task_type && <TaskTypeBadge type={a.task_type} />}
                    </td>
                    <td className="px-4 py-3.5">
                      <AssignmentStatusBadge status={a.status} />
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      {a.reward_paid != null ? (
                        <span className="text-sm font-semibold text-success-400 tabular-nums">
                          +{formatCC(a.reward_paid)}
                        </span>
                      ) : (
                        <span className="text-sm text-neutral-600">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-sm text-neutral-500 hidden md:table-cell">
                      {a.accepted_at ? formatDate(a.accepted_at) : '—'}
                    </td>
                    <td className="px-4 py-3.5 text-sm text-neutral-500 hidden md:table-cell">
                      {a.completed_at ? formatDate(a.completed_at) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Paginación en cliente (todo el historial ya está en memoria) */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-neutral-500">
                Página {page + 1} de {totalPages}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page === 0}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Anterior
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page >= totalPages - 1}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
