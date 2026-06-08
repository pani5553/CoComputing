import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PlusCircleIcon, CheckCircleIcon, InformationCircleIcon } from '@heroicons/react/24/outline'
import { createTask } from '../../api/clientApi'
import { extractErrorMessage } from '../../api/client'
import type { CreateTaskRequest, Difficulty, HardwareRequired, TaskType } from '../../types'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import ErrorAlert from '../../components/ui/ErrorAlert'
import { formatCC } from '../../utils/format'

const TASK_TYPES: { value: TaskType; label: string }[] = [
  { value: 'renderizado_3d', label: 'Renderizado 3D' },
  { value: 'entrenamiento_ml', label: 'Entrenamiento ML' },
  { value: 'transcodificacion_video', label: 'Transcodificación de vídeo' },
  { value: 'analisis_datos', label: 'Análisis de datos' },
  { value: 'simulacion_fisica', label: 'Simulación física' },
]

const DIFFICULTIES: { value: Difficulty; label: string }[] = [
  { value: 'facil', label: 'Fácil' },
  { value: 'medio', label: 'Medio' },
  { value: 'dificil', label: 'Difícil' },
]

const HARDWARE_OPTIONS: { value: HardwareRequired; label: string }[] = [
  { value: 'cpu', label: 'CPU' },
  { value: 'gpu', label: 'GPU' },
  { value: 'mixto', label: 'Mixto (CPU + GPU)' },
]

const DEFAULT_STAGES: Record<TaskType, string[]> = {
  renderizado_3d: ['Preparando entorno', 'Cargando escena', 'Renderizando frames', 'Post-procesado', 'Exportando resultado'],
  entrenamiento_ml: ['Preparando entorno', 'Descargando dataset', 'Entrenando modelo', 'Validando precisión', 'Guardando checkpoints'],
  transcodificacion_video: ['Preparando entorno', 'Analizando vídeo', 'Transcodificando', 'Verificando calidad', 'Empaquetando salida'],
  analisis_datos: ['Preparando entorno', 'Cargando datos', 'Procesando análisis', 'Generando resultados', 'Exportando informe'],
  simulacion_fisica: ['Preparando entorno', 'Configurando simulación', 'Ejecutando cómputo', 'Procesando resultados', 'Generando informe'],
}

interface FormState {
  title: string
  task_type: TaskType
  description: string
  reward: string
  difficulty: Difficulty
  hardware_required: HardwareRequired
  total_slots: string
  duration_min: string
  duration_max: string
  stages: string
  requester_name: string
}

const initialForm: FormState = {
  title: '',
  task_type: 'entrenamiento_ml',
  description: '',
  reward: '',
  difficulty: 'medio',
  hardware_required: 'gpu',
  total_slots: '1',
  duration_min: '30',
  duration_max: '120',
  stages: DEFAULT_STAGES['entrenamiento_ml'].join('\n'),
  requester_name: '',
}

export default function PublishTaskPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState<FormState>(initialForm)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<{ taskId: string; escrowTotal: number; newBalance: number } | null>(null)

  const reward = parseFloat(form.reward) || 0
  const slots = parseInt(form.total_slots) || 0
  const escrowTotal = reward * slots

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) {
    const { name, value } = e.target
    if (name === 'task_type') {
      setForm((prev) => ({
        ...prev,
        task_type: value as TaskType,
        stages: DEFAULT_STAGES[value as TaskType].join('\n'),
      }))
    } else {
      setForm((prev) => ({ ...prev, [name]: value }))
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    const stagesArr = form.stages
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)

    if (stagesArr.length < 1) {
      setError('Añade al menos una etapa de procesamiento.')
      return
    }
    const dMin = parseInt(form.duration_min)
    const dMax = parseInt(form.duration_max)
    if (dMax < dMin) {
      setError('La duración máxima debe ser mayor o igual que la mínima.')
      return
    }

    const payload: CreateTaskRequest = {
      title: form.title.trim(),
      task_type: form.task_type,
      description: form.description.trim(),
      reward: parseFloat(form.reward),
      difficulty: form.difficulty,
      hardware_required: form.hardware_required,
      total_slots: parseInt(form.total_slots),
      duration_min: dMin,
      duration_max: dMax,
      stages: stagesArr,
      requester_name: form.requester_name.trim(),
    }

    setLoading(true)
    try {
      const result = await createTask(payload)
      setSuccess({
        taskId: result.task_id,
        escrowTotal: result.escrow_total,
        newBalance: result.new_available_balance,
      })
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="max-w-md mx-auto mt-12 px-4 text-center">
        <CheckCircleIcon className="h-16 w-16 text-brand-400 mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-neutral-100 mb-2">¡Tarea publicada!</h1>
        <p className="text-neutral-400 mb-1">
          Se han retenido <span className="text-amber-400 font-semibold">{formatCC(success.escrowTotal)}</span> en escrow.
        </p>
        <p className="text-neutral-500 text-sm mb-8">
          Saldo disponible: <span className="text-neutral-300">{formatCC(success.newBalance)}</span>
        </p>
        <div className="flex gap-3 justify-center">
          <Button variant="secondary" onClick={() => navigate('/cliente/mis-tareas')}>
            Ver mis tareas
          </Button>
          <Button onClick={() => navigate(`/cliente/tareas/${success.taskId}`)}>
            Ver detalle
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <div className="flex items-center gap-3 mb-6">
        <PlusCircleIcon className="h-8 w-8 text-brand-400" />
        <div>
          <h1 className="text-2xl font-bold text-neutral-100">Publicar tarea</h1>
          <p className="text-sm text-neutral-400">La tarea aparecerá en el catálogo para los proveedores</p>
        </div>
      </div>

      {escrowTotal > 0 && (
        <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/30 rounded-xl px-4 py-3 mb-6">
          <InformationCircleIcon className="h-5 w-5 text-amber-400 mt-0.5 shrink-0" />
          <p className="text-sm text-amber-300">
            Se retendrán <strong>{formatCC(escrowTotal)}</strong> en escrow ({reward > 0 && slots > 0 ? `${formatCC(reward)} × ${slots} plaza${slots !== 1 ? 's' : ''}` : ''}). Se liberarán conforme los proveedores completen la tarea.
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-neutral-300 uppercase tracking-wide">Información básica</h2>

          <Input
            label="Título"
            name="title"
            value={form.title}
            onChange={handleChange}
            placeholder="Ej: Entrenamiento ResNet-50 sobre CIFAR-100"
            required
          />

          <div>
            <label className="block text-sm font-medium text-neutral-300 mb-1.5">Tipo de tarea</label>
            <select
              name="task_type"
              value={form.task_type}
              onChange={handleChange}
              className="w-full bg-neutral-800 border border-neutral-600 text-neutral-100 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {TASK_TYPES.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-300 mb-1.5">Descripción</label>
            <textarea
              name="description"
              value={form.description}
              onChange={handleChange}
              rows={3}
              placeholder="Describe los requisitos y objetivo de la tarea..."
              required
              className="w-full bg-neutral-800 border border-neutral-600 text-neutral-100 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-y"
            />
          </div>

          <Input
            label="Nombre del solicitante / empresa"
            name="requester_name"
            value={form.requester_name}
            onChange={handleChange}
            placeholder="Ej: AI Research Lab"
            required
          />
        </div>

        <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-neutral-300 uppercase tracking-wide">Recompensa y plazas</h2>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Recompensa por plaza (CC)"
              name="reward"
              type="number"
              min="0.01"
              step="0.01"
              value={form.reward}
              onChange={handleChange}
              placeholder="Ej: 5.00"
              required
            />
            <Input
              label="Nº de plazas"
              name="total_slots"
              type="number"
              min="1"
              max="100"
              value={form.total_slots}
              onChange={handleChange}
              required
            />
          </div>

          {escrowTotal > 0 && (
            <p className="text-sm text-amber-400">
              Escrow total: <strong>{formatCC(escrowTotal)}</strong>
            </p>
          )}
        </div>

        <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-neutral-300 uppercase tracking-wide">Requisitos técnicos</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-1.5">Dificultad</label>
              <select
                name="difficulty"
                value={form.difficulty}
                onChange={handleChange}
                className="w-full bg-neutral-800 border border-neutral-600 text-neutral-100 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                {DIFFICULTIES.map(({ value, label }) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-1.5">Hardware requerido</label>
              <select
                name="hardware_required"
                value={form.hardware_required}
                onChange={handleChange}
                className="w-full bg-neutral-800 border border-neutral-600 text-neutral-100 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                {HARDWARE_OPTIONS.map(({ value, label }) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Duración mínima (min)"
              name="duration_min"
              type="number"
              min="1"
              value={form.duration_min}
              onChange={handleChange}
              required
            />
            <Input
              label="Duración máxima (min)"
              name="duration_max"
              type="number"
              min="1"
              value={form.duration_max}
              onChange={handleChange}
              required
            />
          </div>
        </div>

        <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-5 space-y-3">
          <h2 className="text-sm font-semibold text-neutral-300 uppercase tracking-wide">Etapas de procesamiento</h2>
          <p className="text-xs text-neutral-500">Una etapa por línea (mín. 1)</p>
          <textarea
            name="stages"
            value={form.stages}
            onChange={handleChange}
            rows={5}
            className="w-full bg-neutral-800 border border-neutral-600 text-neutral-100 rounded-lg px-3 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500 resize-y"
          />
        </div>

        {error && <ErrorAlert message={error} />}

        <div className="flex gap-3 justify-end">
          <Button type="button" variant="secondary" onClick={() => navigate('/cliente/mis-tareas')}>
            Cancelar
          </Button>
          <Button type="submit" loading={loading}>
            Publicar tarea
          </Button>
        </div>
      </form>
    </div>
  )
}
