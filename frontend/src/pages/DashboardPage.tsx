import { useEffect, useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import {
  ChartBarIcon,
  CheckCircleIcon,
  BanknotesIcon,
  WalletIcon,
  BriefcaseIcon,
} from '@heroicons/react/24/outline'
import { useAuthStore } from '../store/authStore'
import { getHistory } from '../api/tasks'
import { getWallet } from '../api/wallet'
import { extractErrorMessage } from '../api/client'
import type { Assignment } from '../types'
import type { Wallet } from '../types'
import { RankBadge, AssignmentStatusBadge, TaskTypeBadge } from '../components/ui/Badge'
import { SkeletonStat, SkeletonRow } from '../components/ui/SkeletonCard'
import ErrorAlert from '../components/ui/ErrorAlert'
import Button from '../components/ui/Button'
import EmptyState from '../components/ui/EmptyState'
import Modal from '../components/ui/Modal'
import { formatCC, formatDate } from '../utils/format'

export default function DashboardPage() {
  const provider = useAuthStore((s) => s.provider)
  const navigate = useNavigate()
  const location = useLocation()

  const [history, setHistory] = useState<Assignment[]>([])
  const [wallet, setWallet] = useState<Wallet | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Modal de éxito post-completar
  const [successModal, setSuccessModal] = useState<{
    open: boolean
    taskCompleted?: boolean
    taskFailed?: boolean
  }>({ open: false })

  // Detectar si venimos de ProcessingPage con resultado
  useEffect(() => {
    const state = location.state as {
      taskCompleted?: boolean
      taskFailed?: boolean
      assignmentId?: string
    } | null

    if (state?.taskCompleted || state?.taskFailed) {
      setSuccessModal({
        open: true,
        taskCompleted: state.taskCompleted,
        taskFailed: state.taskFailed,
      })
      // Limpiar el state de location para evitar que se vuelva a mostrar
      window.history.replaceState({}, '')
    }
  }, [location.state])

  async function loadData() {
    setLoading(true)
    setError(null)
    try {
      const [histData, walletData] = await Promise.all([getHistory(), getWallet()])
      setHistory(histData.assignments.slice(0, 5))
      setWallet(walletData)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const today = new Date().toLocaleDateString('es-ES', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

  return (
    <div className="animate-fade-in space-y-8">
      {/* Cabecera */}
      <div>
        <h1 className="text-2xl font-bold text-neutral-100">
          Bienvenido, {provider?.full_name?.split(' ')[0] ?? 'proveedor'}
        </h1>
        <p className="text-sm text-neutral-500 mt-1 capitalize">{today}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {loading ? (
          <>
            <SkeletonStat />
            <SkeletonStat />
            <SkeletonStat />
          </>
        ) : error ? null : (
          <>
            {/* Trust Score */}
            <div className="flex flex-col gap-1 p-5 rounded-xl bg-neutral-900 border border-neutral-700">
              <div className="flex items-center gap-2">
                <ChartBarIcon className="h-5 w-5 text-neutral-500" aria-hidden="true" />
                <span className="text-xs text-neutral-500 uppercase tracking-wide font-medium">
                  Trust Score
                </span>
              </div>
              <p className="text-3xl font-bold text-neutral-100 tabular-nums mt-1">
                {provider?.trust_score?.toFixed(2) ?? '0.00'}
              </p>
              {provider?.rank && (
                <div className="mt-1">
                  <RankBadge rank={provider.rank} size="sm" />
                </div>
              )}
            </div>

            {/* Tareas completadas */}
            <div className="flex flex-col gap-1 p-5 rounded-xl bg-neutral-900 border border-neutral-700">
              <div className="flex items-center gap-2">
                <CheckCircleIcon className="h-5 w-5 text-neutral-500" aria-hidden="true" />
                <span className="text-xs text-neutral-500 uppercase tracking-wide font-medium">
                  Tareas completadas
                </span>
              </div>
              <p className="text-3xl font-bold text-neutral-100 tabular-nums mt-1">
                {provider?.tasks_completed ?? 0}
              </p>
              <p className="text-sm text-neutral-400">
                Tasa de éxito: {provider?.success_rate?.toFixed(1) ?? '0.0'}%
              </p>
            </div>

            {/* Ganancias */}
            <div className="flex flex-col gap-1 p-5 rounded-xl bg-neutral-900 border border-neutral-700">
              <div className="flex items-center gap-2">
                <BanknotesIcon className="h-5 w-5 text-neutral-500" aria-hidden="true" />
                <span className="text-xs text-neutral-500 uppercase tracking-wide font-medium">
                  Ganancias totales
                </span>
              </div>
              <p className="text-3xl font-bold text-success-400 tabular-nums mt-1">
                {formatCC(provider?.total_earned ?? 0)}
              </p>
              {wallet && (
                <p className="text-sm text-success-500">
                  Disponible: {formatCC(wallet.available_balance)}
                </p>
              )}
            </div>
          </>
        )}
      </div>

      {error && (
        <ErrorAlert message={error} onRetry={loadData} />
      )}

      {/* Cartera resumen */}
      {!loading && !error && wallet && (
        <div className="p-5 rounded-xl bg-neutral-900 border border-neutral-700">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <WalletIcon className="h-5 w-5 text-neutral-400" aria-hidden="true" />
              <h2 className="text-base font-semibold text-neutral-200">Cartera</h2>
            </div>
            <Link
              to="/cartera"
              className="text-sm text-brand-400 hover:text-brand-300 font-medium underline-offset-2 hover:underline transition-colors"
            >
              Ir a mi cartera →
            </Link>
          </div>
          <div className="border-t border-neutral-700 pt-4 grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-neutral-500 uppercase tracking-wide">Saldo disponible</p>
              <p className="text-2xl font-bold text-success-400 tabular-nums mt-0.5">
                {formatCC(wallet.available_balance)}
              </p>
            </div>
            <div>
              <p className="text-xs text-neutral-500 uppercase tracking-wide">Saldo pendiente</p>
              <p className="text-xl font-bold text-neutral-400 tabular-nums mt-0.5">
                {formatCC(wallet.pending_balance)}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Actividad reciente */}
      <div>
        <h2 className="text-xl font-semibold text-neutral-100 mb-4">Actividad reciente</h2>

        {loading ? (
          <div className="w-full border border-neutral-700 rounded-xl overflow-hidden">
            <table className="w-full">
              <tbody>
                {Array.from({ length: 5 }).map((_, i) => (
                  <SkeletonRow key={i} />
                ))}
              </tbody>
            </table>
          </div>
        ) : error ? null : history.length === 0 ? (
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
                      Fecha
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((a) => (
                    <tr
                      key={a.id}
                      className="border-b border-neutral-800 last:border-0 hover:bg-neutral-800/50 transition-colors duration-100"
                    >
                      <td className="px-4 py-3.5 text-sm text-neutral-300 max-w-[200px] truncate">
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
                        {a.completed_at
                          ? formatDate(a.completed_at)
                          : a.accepted_at
                          ? formatDate(a.accepted_at)
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4">
              <Link
                to="/tareas"
                className="inline-flex items-center gap-1 text-brand-400 hover:text-brand-300 text-sm font-medium underline-offset-2 hover:underline transition-colors"
              >
                Explorar todas las tareas disponibles →
              </Link>
            </div>
          </>
        )}
      </div>

      {/* Modal de éxito post-completar */}
      <Modal
        isOpen={successModal.open}
        onClose={() => setSuccessModal({ open: false })}
        title={successModal.taskCompleted ? '¡Tarea completada!' : 'Tarea fallida'}
      >
        {successModal.taskCompleted ? (
          <div className="text-center space-y-4">
            <CheckCircleIcon className="h-16 w-16 text-success-400 mx-auto" aria-hidden="true" />
            <div>
              <p className="text-sm text-neutral-400">Tu saldo disponible ha sido actualizado.</p>
            </div>
            <div className="border-t border-neutral-700 pt-4 flex justify-end gap-3">
              <Button variant="secondary" onClick={() => setSuccessModal({ open: false })}>
                Volver al dashboard
              </Button>
              <Button variant="primary" onClick={() => { setSuccessModal({ open: false }); navigate('/cartera') }}>
                Ver mi cartera
              </Button>
            </div>
          </div>
        ) : (
          <div className="text-center space-y-4">
            <p className="text-sm text-neutral-400">
              La tarea ha sido marcada como fallida. Tu Trust Score puede haberse visto afectado.
            </p>
            <div className="border-t border-neutral-700 pt-4 flex justify-end">
              <Button variant="secondary" onClick={() => setSuccessModal({ open: false })}>
                Entendido
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
