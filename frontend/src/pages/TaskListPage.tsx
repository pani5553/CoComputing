import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FunnelIcon,
  ClockIcon,
  UserGroupIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline'
import { getTasks } from '../api/tasks'
import { extractErrorMessage } from '../api/client'
import type { Task, TaskFilters, Difficulty, HardwareRequired, TaskType } from '../types'
import SkeletonCard from '../components/ui/SkeletonCard'
import ErrorAlert from '../components/ui/ErrorAlert'
import EmptyState from '../components/ui/EmptyState'
import Button from '../components/ui/Button'
import {
  DifficultyBadge,
  HardwareBadge,
  TaskTypeBadge,
  AssignmentStatusBadge,
} from '../components/ui/Badge'
import { formatCC } from '../utils/format'

const DIFFICULTY_OPTIONS: { value: Difficulty; label: string }[] = [
  { value: 'facil', label: 'Fácil' },
  { value: 'medio', label: 'Medio' },
  { value: 'dificil', label: 'Difícil' },
]

const HARDWARE_OPTIONS: { value: HardwareRequired; label: string }[] = [
  { value: 'cpu', label: 'CPU' },
  { value: 'gpu', label: 'GPU' },
  { value: 'mixto', label: 'Mixto' },
]

const TASK_TYPE_OPTIONS: { value: TaskType | ''; label: string }[] = [
  { value: '', label: 'Todos los tipos' },
  { value: 'renderizado_3d', label: 'Renderizado 3D' },
  { value: 'entrenamiento_ml', label: 'Entrenamiento ML' },
  { value: 'transcodificacion_video', label: 'Transcodificación' },
  { value: 'analisis_datos', label: 'Análisis de datos' },
  { value: 'simulacion_fisica', label: 'Simulación física' },
]

export default function TaskListPage() {
  const navigate = useNavigate()
  const [tasks, setTasks] = useState<Task[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filtros
  const [selectedDifficulty, setSelectedDifficulty] = useState<Difficulty[]>([])
  const [selectedHardware, setSelectedHardware] = useState<HardwareRequired[]>([])
  const [selectedType, setSelectedType] = useState<TaskType | ''>('')
  const [minReward, setMinReward] = useState<string>('')

  const hasActiveFilters =
    selectedDifficulty.length > 0 ||
    selectedHardware.length > 0 ||
    selectedType !== '' ||
    minReward !== ''

  const fetchTasks = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const filters: TaskFilters = {}
      if (selectedDifficulty.length > 0) filters.difficulty = selectedDifficulty.join(',')
      if (selectedHardware.length > 0) filters.hardware = selectedHardware.join(',')
      if (selectedType) filters.task_type = selectedType
      const parsed = parseFloat(minReward)
      if (!isNaN(parsed) && parsed > 0) filters.min_reward = parsed

      const data = await getTasks(filters)
      setTasks(data.tasks)
      setCount(data.count)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [selectedDifficulty, selectedHardware, selectedType, minReward])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  function clearFilters() {
    setSelectedDifficulty([])
    setSelectedHardware([])
    setSelectedType('')
    setMinReward('')
  }

  function toggleDifficulty(d: Difficulty) {
    setSelectedDifficulty((prev) =>
      prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d],
    )
  }

  function toggleHardware(h: HardwareRequired) {
    setSelectedHardware((prev) =>
      prev.includes(h) ? prev.filter((x) => x !== h) : [...prev, h],
    )
  }

  return (
    <div className="animate-fade-in space-y-6">
      {/* Cabecera */}
      <div>
        <h1 className="text-2xl font-bold text-neutral-100">Tareas disponibles</h1>
        {!loading && !error && (
          <p className="text-sm text-neutral-500 mt-1">
            {count === 0 ? 'Sin resultados' : `${count} ${count === 1 ? 'tarea encontrada' : 'tareas encontradas'}`}
          </p>
        )}
      </div>

      {/* Panel de filtros */}
      <div className="bg-neutral-900 rounded-xl border border-neutral-700 p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Dificultad */}
          <div>
            <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
              Dificultad
            </p>
            <div className="flex flex-wrap gap-2">
              {DIFFICULTY_OPTIONS.map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => toggleDifficulty(value)}
                  className={`px-3 py-1.5 rounded text-xs font-medium border transition-all duration-150 ${
                    selectedDifficulty.includes(value)
                      ? 'bg-brand-600 border-brand-500 text-white'
                      : 'bg-neutral-800 border-neutral-700 text-neutral-400 hover:border-neutral-500 hover:text-neutral-300'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Hardware */}
          <div>
            <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
              Hardware
            </p>
            <div className="flex flex-wrap gap-2">
              {HARDWARE_OPTIONS.map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => toggleHardware(value)}
                  className={`px-3 py-1.5 rounded text-xs font-medium border transition-all duration-150 ${
                    selectedHardware.includes(value)
                      ? 'bg-brand-600 border-brand-500 text-white'
                      : 'bg-neutral-800 border-neutral-700 text-neutral-400 hover:border-neutral-500 hover:text-neutral-300'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Tipo de tarea */}
          <div>
            <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
              Tipo de tarea
            </p>
            <div className="relative">
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value as TaskType | '')}
                className="w-full px-4 py-2.5 rounded-lg bg-neutral-800 border border-neutral-700 text-neutral-300 text-sm focus:outline-none focus:border-brand-500 cursor-pointer appearance-none"
              >
                {TASK_TYPE_OPTIONS.map(({ value, label }) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <span className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
                <svg className="h-4 w-4 text-neutral-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </span>
            </div>
          </div>

          {/* Recompensa mínima */}
          <div>
            <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
              Recompensa mínima
            </p>
            <div className="relative">
              <input
                type="number"
                min="0"
                step="0.01"
                placeholder="0,00"
                value={minReward}
                onChange={(e) => setMinReward(e.target.value)}
                className="w-full px-4 py-2.5 pr-12 rounded-lg bg-neutral-800 border border-neutral-700 text-neutral-100 placeholder:text-neutral-500 text-sm focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 text-sm select-none">
                CC
              </span>
            </div>
          </div>
        </div>

        {hasActiveFilters && (
          <div className="mt-3 pt-3 border-t border-neutral-800 flex items-center gap-2 flex-wrap">
            <span className="text-xs text-neutral-500">Filtros activos:</span>
            {selectedDifficulty.map((d) => (
              <span key={d} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border border-brand-500/50 text-brand-400 bg-brand-500/5">
                {DIFFICULTY_OPTIONS.find((o) => o.value === d)?.label}
                <button
                  onClick={() => toggleDifficulty(d)}
                  className="hover:text-brand-200 focus:outline-none"
                  aria-label={`Quitar filtro ${d}`}
                >×</button>
              </span>
            ))}
            {selectedHardware.map((h) => (
              <span key={h} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border border-brand-500/50 text-brand-400 bg-brand-500/5">
                {HARDWARE_OPTIONS.find((o) => o.value === h)?.label}
                <button
                  onClick={() => toggleHardware(h)}
                  className="hover:text-brand-200 focus:outline-none"
                  aria-label={`Quitar filtro ${h}`}
                >×</button>
              </span>
            ))}
            {selectedType && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border border-brand-500/50 text-brand-400 bg-brand-500/5">
                {TASK_TYPE_OPTIONS.find((o) => o.value === selectedType)?.label}
                <button onClick={() => setSelectedType('')} className="hover:text-brand-200 focus:outline-none" aria-label="Quitar filtro de tipo">×</button>
              </span>
            )}
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              Limpiar todo
            </Button>
          </div>
        )}
      </div>

      {/* Error */}
      {error && <ErrorAlert message={error} onRetry={fetchTasks} />}

      {/* Lista de tareas */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} lines={5} />
          ))}
        </div>
      ) : !error && tasks.length === 0 ? (
        <div className="bg-neutral-900 border border-neutral-700 rounded-xl">
          <EmptyState
            icon={<FunnelIcon className="h-12 w-12" />}
            title="No hay tareas disponibles con estos filtros."
            action={
              hasActiveFilters
                ? { label: 'Limpiar filtros', onClick: clearFilters }
                : undefined
            }
            actionVariant="secondary"
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onClick={() => navigate(`/tareas/${task.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function TaskCard({ task, onClick }: { task: Task; onClick: () => void }) {
  const hasActiveAssignment =
    task.active_assignment &&
    (task.active_assignment.status === 'aceptada' ||
      task.active_assignment.status === 'procesando')

  return (
    <article
      onClick={onClick}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
      role="button"
      tabIndex={0}
      aria-label={`Ver tarea: ${task.title}`}
      className="group flex flex-col gap-3 p-5 rounded-xl bg-neutral-900 border border-neutral-700 hover:border-brand-500/50 hover:bg-neutral-800/80 cursor-pointer transition-all duration-150 hover:shadow-lg hover:shadow-brand-500/5 focus:outline-none focus:ring-2 focus:ring-brand-500"
    >
      {/* Badges superiores */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <TaskTypeBadge type={task.task_type} />
        <DifficultyBadge difficulty={task.difficulty} />
      </div>

      {/* Título */}
      <h2 className="text-lg font-semibold text-neutral-100 leading-tight line-clamp-2">
        {task.title}
      </h2>

      {/* Meta info */}
      <div className="flex items-center gap-3 flex-wrap">
        <HardwareBadge hardware={task.hardware_required} />
        <span className="flex items-center gap-1 text-xs text-neutral-500">
          <ClockIcon className="h-3.5 w-3.5" aria-hidden="true" />
          {task.duration_min}–{task.duration_max} min
        </span>
        <span className="flex items-center gap-1 text-xs text-neutral-500">
          <UserGroupIcon className="h-3.5 w-3.5" aria-hidden="true" />
          {task.slots_left} {task.slots_left === 1 ? 'plaza' : 'plazas'}
        </span>
      </div>

      {/* Estado si tiene asignación activa */}
      {hasActiveAssignment && (
        <div>
          <AssignmentStatusBadge status={task.active_assignment!.status} />
        </div>
      )}

      <div className="border-t border-neutral-800 pt-3 flex items-center justify-between">
        <div>
          <p className="text-xs text-neutral-500 uppercase tracking-wide">Recompensa</p>
          <p className="text-xl font-bold text-success-400 tabular-nums">{formatCC(task.reward)}</p>
        </div>
        <ChevronRightIcon
          className="h-5 w-5 text-neutral-600 group-hover:text-brand-400 transition-colors"
          aria-hidden="true"
        />
      </div>
    </article>
  )
}
