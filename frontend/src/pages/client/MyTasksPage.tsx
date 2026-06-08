import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  BriefcaseIcon,
  PlusIcon,
  BanknotesIcon,
  InboxIcon,
} from '@heroicons/react/24/outline'
import { getMyTasks } from '../../api/clientApi'
import { extractErrorMessage } from '../../api/client'
import type { ClientTaskSummary } from '../../types'
import Button from '../../components/ui/Button'
import ErrorAlert from '../../components/ui/ErrorAlert'
import EmptyState from '../../components/ui/EmptyState'
import SkeletonCard from '../../components/ui/SkeletonCard'
import { formatCC, formatDate } from '../../utils/format'
import { clsx } from 'clsx'

const STATUS_LABEL: Record<string, { label: string; classes: string }> = {
  disponible: { label: 'Disponible', classes: 'text-emerald-400 bg-emerald-400/10 border-emerald-600' },
  en_progreso: { label: 'En progreso', classes: 'text-blue-400 bg-blue-400/10 border-blue-600' },
  completada: { label: 'Completada', classes: 'text-neutral-400 bg-neutral-400/10 border-neutral-600' },
  cancelada: { label: 'Cancelada', classes: 'text-red-400 bg-red-400/10 border-red-600' },
}

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_LABEL[status] ?? STATUS_LABEL.disponible
  return (
    <span className={clsx('text-xs px-2 py-0.5 rounded border font-semibold uppercase tracking-wide', cfg.classes)}>
      {cfg.label}
    </span>
  )
}

export default function MyTasksPage() {
  const navigate = useNavigate()
  const [tasks, setTasks] = useState<ClientTaskSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    getMyTasks()
      .then((data) => setTasks(data.tasks))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <BriefcaseIcon className="h-8 w-8 text-brand-400" />
          <div>
            <h1 className="text-2xl font-bold text-neutral-100">Mis tareas publicadas</h1>
            <p className="text-sm text-neutral-400">Tareas que has publicado al catálogo</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            onClick={() => navigate('/cliente/recargar')}
            className="flex items-center gap-1.5"
          >
            <BanknotesIcon className="h-4 w-4" />
            Recargar
          </Button>
          <Button
            onClick={() => navigate('/cliente/publicar')}
            className="flex items-center gap-1.5"
          >
            <PlusIcon className="h-4 w-4" />
            Publicar tarea
          </Button>
        </div>
      </div>

      {error && <ErrorAlert message={error} className="mb-4" />}

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => <SkeletonCard key={i} />)}
        </div>
      ) : tasks.length === 0 ? (
        <EmptyState
          icon={<InboxIcon className="h-12 w-12" />}
          title="No has publicado ninguna tarea"
          description="Publica tu primera tarea y los proveedores de la red la procesarán."
          action={{ label: 'Publicar tarea', onClick: () => navigate('/cliente/publicar') }}
        />
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => (
            <Link
              key={task.id}
              to={`/cliente/tareas/${task.id}`}
              className="block bg-neutral-900 border border-neutral-700 rounded-xl p-5 hover:border-neutral-500 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <StatusBadge status={task.status} />
                  </div>
                  <h3 className="font-semibold text-neutral-100 truncate">{task.title}</h3>
                  <p className="text-xs text-neutral-500 mt-0.5">{formatDate(task.created_at)}</p>
                </div>
                <div className="text-right shrink-0 space-y-1">
                  <p className="text-sm font-semibold text-brand-400">{formatCC(task.reward)}/plaza</p>
                  <p className="text-xs text-neutral-500">
                    {task.slots_completed}/{task.total_slots} completadas
                  </p>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-neutral-800 flex items-center gap-6 text-xs text-neutral-500">
                <span>
                  Escrow retenido: <span className="text-amber-400 font-medium">{formatCC(task.escrow_held)}</span>
                </span>
                <span>
                  Liberado: <span className="text-emerald-400 font-medium">{formatCC(task.escrow_released)}</span>
                </span>
                <span>
                  Plazas libres: <span className="text-neutral-300">{task.slots_left}</span>
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
