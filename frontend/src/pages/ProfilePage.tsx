import { useEffect, useState } from 'react'
import {
  UserCircleIcon,
  CpuChipIcon,
  RectangleGroupIcon,
  CircleStackIcon,
  ArchiveBoxIcon,
  LockClosedIcon,
  UserIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline'
import { BoltIcon as BoltSolid, StarIcon as StarSolid } from '@heroicons/react/24/solid'
import { getStats, updateHardware, setOnline, updateName } from '../api/profile'
import { extractErrorMessage } from '../api/client'
import { useAuthStore } from '../store/authStore'
import type { ProfileStats } from '../types'
import SkeletonCard from '../components/ui/SkeletonCard'
import ErrorAlert from '../components/ui/ErrorAlert'
import { SuccessAlert } from '../components/ui/ErrorAlert'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import ProgressBar from '../components/ui/ProgressBar'
import { RankBadge } from '../components/ui/Badge'
import { formatDate } from '../utils/format'

export default function ProfilePage() {
  const updateProvider = useAuthStore((s) => s.updateProvider)
  const [stats, setStats] = useState<ProfileStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Datos personales
  const [fullName, setFullName] = useState('')
  const [savingName, setSavingName] = useState(false)
  const [nameSuccess, setNameSuccess] = useState(false)
  const [nameError, setNameError] = useState<string | null>(null)

  // Online toggle
  const [toggling, setToggling] = useState(false)

  // Hardware
  const [cpuModel, setCpuModel] = useState('')
  const [gpuModel, setGpuModel] = useState('')
  const [ramGb, setRamGb] = useState('')
  const [storageGb, setStorageGb] = useState('')
  const [savingHardware, setSavingHardware] = useState(false)
  const [hardwareSuccess, setHardwareSuccess] = useState(false)
  const [hardwareError, setHardwareError] = useState<string | null>(null)
  const [hwFieldErrors, setHwFieldErrors] = useState<{
    cpu_model?: string
    ram_gb?: string
    storage_gb?: string
  }>({})

  // Panel de rangos expandido
  const [ranksExpanded, setRanksExpanded] = useState(false)

  async function loadStats() {
    setLoading(true)
    setError(null)
    try {
      const data = await getStats()
      setStats(data)
      setFullName(data.full_name)
      setCpuModel(data.hardware.cpu_model ?? '')
      setGpuModel(data.hardware.gpu_model ?? '')
      setRamGb(data.hardware.ram_gb != null ? String(data.hardware.ram_gb) : '')
      setStorageGb(data.hardware.storage_gb != null ? String(data.hardware.storage_gb) : '')
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStats()
  }, [])

  async function handleSaveName() {
    if (!fullName.trim()) {
      setNameError('El nombre no puede estar vacío.')
      return
    }
    setNameError(null)
    setNameSuccess(false)
    setSavingName(true)
    try {
      const res = await updateName(fullName.trim())
      updateProvider({ full_name: res.full_name })
      setStats((prev) => prev ? { ...prev, full_name: res.full_name } : prev)
      setNameSuccess(true)
      setTimeout(() => setNameSuccess(false), 3000)
    } catch (err) {
      setNameError(extractErrorMessage(err))
    } finally {
      setSavingName(false)
    }
  }

  async function handleToggleOnline() {
    if (!stats) return
    setToggling(true)
    try {
      const res = await setOnline(!stats.is_online)
      updateProvider({ is_online: res.is_online })
      setStats((prev) => prev ? { ...prev, is_online: res.is_online } : prev)
    } catch {
      // silencioso
    } finally {
      setToggling(false)
    }
  }

  function validateHardware() {
    const errors: typeof hwFieldErrors = {}
    if (!cpuModel.trim()) errors.cpu_model = 'El modelo de CPU es obligatorio.'
    const ram = parseInt(ramGb)
    if (!ramGb || isNaN(ram) || ram < 1) errors.ram_gb = 'Introduce un valor válido (mínimo 1 GB).'
    const storage = parseInt(storageGb)
    if (!storageGb || isNaN(storage) || storage < 1) errors.storage_gb = 'Introduce un valor válido (mínimo 1 GB).'
    return errors
  }

  async function handleSaveHardware() {
    const errors = validateHardware()
    setHwFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setHardwareError(null)
    setHardwareSuccess(false)
    setSavingHardware(true)
    try {
      await updateHardware({
        cpu_model: cpuModel.trim(),
        gpu_model: gpuModel.trim() || null,
        ram_gb: parseInt(ramGb),
        storage_gb: parseInt(storageGb),
      })
      setHardwareSuccess(true)
      setTimeout(() => setHardwareSuccess(false), 3000)
      // Refrescar stats
      await loadStats()
    } catch (err) {
      setHardwareError(extractErrorMessage(err))
    } finally {
      setSavingHardware(false)
    }
  }

  const rankDescriptions: Record<string, string> = {
    nuevo: 'Proveedor en periodo de prueba. Completa tareas para subir de rango.',
    confiable: 'Proveedor con historial positivo. La plataforma confía en tu trabajo.',
    experto: 'Proveedor de alto rendimiento. Acceso prioritario a tareas premium.',
    elite: 'El nivel más alto de confianza. Eres parte del grupo de élite de Co-Computing.',
  }

  if (loading) {
    return (
      <div className="animate-fade-in space-y-6">
        <h1 className="text-2xl font-bold text-neutral-100">Mi perfil</h1>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonCard lines={8} />
          <SkeletonCard lines={8} />
        </div>
        <SkeletonCard lines={6} />
      </div>
    )
  }

  if (error || !stats) {
    return (
      <div className="animate-fade-in space-y-4">
        <h1 className="text-2xl font-bold text-neutral-100">Mi perfil</h1>
        <ErrorAlert
          message={error ?? 'No se pudieron cargar los datos de tu perfil.'}
          onRetry={loadStats}
        />
      </div>
    )
  }

  const detail = stats.trust_score_detail
  const rankInfo = stats.rank_info

  return (
    <div className="animate-fade-in space-y-8">
      <h1 className="text-2xl font-bold text-neutral-100">Mi perfil</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ── Datos personales ── */}
        <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-6 space-y-5">
          <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">
            Datos personales
          </h2>
          <div className="border-t border-neutral-700 pt-5">
            {/* Avatar + nombre */}
            <div className="flex items-center gap-4 mb-6">
              <UserCircleIcon className="h-16 w-16 text-neutral-600 flex-shrink-0" aria-hidden="true" />
              <div>
                <p className="text-xl font-semibold text-neutral-100">{stats.full_name}</p>
                <p className="text-xs text-neutral-500 mt-0.5">
                  Miembro desde {formatDate(stats.created_at)}
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {/* Nombre editable */}
              <Input
                label="Nombre completo"
                id="profile-name"
                type="text"
                value={fullName}
                onChange={(e) => {
                  setFullName(e.target.value)
                  setNameError(null)
                }}
                error={nameError ?? undefined}
                disabled={savingName}
              />

              {nameSuccess && (
                <SuccessAlert message="Nombre actualizado correctamente." />
              )}

              {/* Email (solo lectura) */}
              <div>
                <label
                  htmlFor="profile-email"
                  className="block text-sm font-medium text-neutral-300 mb-1.5"
                >
                  Correo electrónico
                </label>
                <div className="relative">
                  <input
                    id="profile-email"
                    type="email"
                    value={stats.email}
                    readOnly
                    disabled
                    className="w-full px-4 py-2.5 pr-10 rounded-lg bg-neutral-800 border border-neutral-700 text-neutral-500 text-sm cursor-not-allowed"
                  />
                  <LockClosedIcon
                    className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-600"
                    aria-hidden="true"
                  />
                </div>
              </div>

              {/* Estado online */}
              <div>
                <p className="text-sm font-medium text-neutral-300 mb-2">
                  Estado de disponibilidad
                </p>
                <div className="flex items-center gap-3">
                  <button
                    role="switch"
                    aria-checked={stats.is_online}
                    disabled={toggling}
                    onClick={handleToggleOnline}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 focus:ring-offset-neutral-900 disabled:opacity-50 ${
                      stats.is_online ? 'bg-success-500' : 'bg-neutral-700'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ${
                        stats.is_online ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                  <span
                    className={`text-sm font-medium ${stats.is_online ? 'text-success-400' : 'text-neutral-500'}`}
                  >
                    {stats.is_online ? 'Online' : 'Offline'}
                  </span>
                </div>
              </div>

              {/* Tasa de éxito */}
              <p className="text-sm text-neutral-500">
                Tasa de éxito: <span className="text-neutral-300 font-medium">{stats.success_rate.toFixed(1)}%</span>
              </p>

              <Button
                variant="primary"
                loading={savingName}
                onClick={handleSaveName}
              >
                {savingName ? 'Guardando...' : 'Guardar cambios'}
              </Button>
            </div>
          </div>
        </div>

        {/* ── Trust Score ── */}
        <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-6 space-y-5">
          <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">
            Trust Score
          </h2>
          <div className="border-t border-neutral-700 pt-5 space-y-4">
            {/* Número grande */}
            <p className="text-4xl font-bold text-neutral-100 tabular-nums">
              {stats.trust_score.toFixed(2)}
            </p>

            <RankBadge rank={stats.rank} size="md" />

            <p className="text-sm text-neutral-500 italic">
              {rankDescriptions[stats.rank]}
            </p>

            <div className="border-t border-neutral-700 pt-4 space-y-3">
              {/* Componentes del trust score */}
              {[
                {
                  label: 'Tasa de completado',
                  value: detail.completion_rate,
                  weight: detail.completion_rate_weight,
                },
                {
                  label: 'Precisión',
                  value: detail.accuracy,
                  weight: detail.accuracy_weight,
                },
                {
                  label: 'Tiempo de respuesta',
                  value: detail.response_time_score,
                  weight: detail.response_time_weight,
                },
                {
                  label: 'Valoración cliente',
                  value: detail.client_rating,
                  weight: detail.client_rating_weight,
                },
              ].map(({ label, value, weight }) => (
                <div key={label}>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs text-neutral-400">
                      {label}{' '}
                      <span className="text-neutral-600">({Math.round(weight * 100)}%)</span>
                    </span>
                    <span className="text-xs font-medium text-neutral-300 tabular-nums">
                      {value.toFixed(0)}
                    </span>
                  </div>
                  <ProgressBar
                    value={value}
                    variant="rank"
                    rank={stats.rank}
                    size="sm"
                  />
                </div>
              ))}
            </div>

            {/* Siguiente rango */}
            {rankInfo.next_rank && rankInfo.points_to_next_rank != null && (
              <div className="border-t border-neutral-700 pt-4">
                <p className="text-sm text-neutral-400">
                  Siguiente rango:{' '}
                  <span className="font-semibold text-neutral-200 capitalize">
                    {rankInfo.next_rank === 'elite' ? 'Élite' : rankInfo.next_rank.charAt(0).toUpperCase() + rankInfo.next_rank.slice(1)}
                  </span>
                </p>
                <p className="text-xs text-neutral-500 mt-1">
                  Te faltan{' '}
                  <span className="font-semibold text-neutral-300 tabular-nums">
                    {rankInfo.points_to_next_rank.toFixed(2)} puntos
                  </span>{' '}
                  para llegar a{' '}
                  {rankInfo.next_rank === 'elite' ? 'Élite' : rankInfo.next_rank}.
                </p>
              </div>
            )}

            {/* Panel de rangos expandible */}
            <div className="border-t border-neutral-700 pt-4">
              <button
                onClick={() => setRanksExpanded((v) => !v)}
                className="text-sm text-brand-400 hover:text-brand-300 font-medium underline-offset-2 hover:underline transition-colors focus:outline-none"
              >
                {ranksExpanded ? 'Ocultar desglose de rangos ▲' : 'Ver desglose de rangos ▾'}
              </button>

              {ranksExpanded && (
                <div className="mt-3 space-y-2 animate-fade-in">
                  {[
                    { rank: 'nuevo', min: 0, max: 49, icon: <UserIcon className="h-4 w-4" />, desc: 'Proveedor en prueba' },
                    { rank: 'confiable', min: 50, max: 74, icon: <ShieldCheckIcon className="h-4 w-4" />, desc: 'Historial positivo' },
                    { rank: 'experto', min: 75, max: 89, icon: <BoltSolid className="h-4 w-4" />, desc: 'Alto rendimiento' },
                    { rank: 'elite', min: 90, max: 100, icon: <StarSolid className="h-4 w-4" />, desc: 'Máxima confianza' },
                  ].map(({ rank, min, max, icon, desc }) => (
                    <div
                      key={rank}
                      className={`flex items-center gap-3 p-2.5 rounded-lg ${
                        stats.rank === rank ? 'bg-neutral-800 border border-neutral-600' : ''
                      }`}
                    >
                      <span className="text-neutral-500 flex-shrink-0">{icon}</span>
                      <div className="flex-1 min-w-0">
                        <span className="text-xs font-semibold text-neutral-300 capitalize">
                          {rank === 'elite' ? 'Élite' : rank.charAt(0).toUpperCase() + rank.slice(1)}
                        </span>
                        <span className="text-xs text-neutral-600 ml-2">{min}–{max}</span>
                        <p className="text-xs text-neutral-500">{desc}</p>
                      </div>
                      {stats.rank === rank && (
                        <span className="text-xs text-brand-400 font-semibold flex-shrink-0">← Tú</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── Hardware ── */}
      <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-6 space-y-5">
        <h2 className="text-xl font-semibold text-neutral-100">Hardware registrado</h2>
        <div className="border-t border-neutral-700 pt-5 space-y-5">
          {hardwareSuccess && (
            <SuccessAlert message="Hardware actualizado correctamente." />
          )}
          {hardwareError && (
            <ErrorAlert message={hardwareError} />
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* CPU */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm text-neutral-400">
                <CpuChipIcon className="h-4 w-4" aria-hidden="true" />
                <span>Modelo de CPU *</span>
              </div>
              <Input
                id="cpu-model"
                type="text"
                placeholder="Intel Core i9-14900K"
                value={cpuModel}
                onChange={(e) => {
                  setCpuModel(e.target.value)
                  if (hwFieldErrors.cpu_model) setHwFieldErrors((p) => ({ ...p, cpu_model: undefined }))
                }}
                error={hwFieldErrors.cpu_model}
                disabled={savingHardware}
              />
            </div>

            {/* GPU */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm text-neutral-400">
                <RectangleGroupIcon className="h-4 w-4" aria-hidden="true" />
                <span>Modelo de GPU (opcional)</span>
              </div>
              <Input
                id="gpu-model"
                type="text"
                placeholder="NVIDIA GeForce RTX 4090"
                value={gpuModel}
                onChange={(e) => setGpuModel(e.target.value)}
                disabled={savingHardware}
              />
            </div>

            {/* RAM */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm text-neutral-400">
                <CircleStackIcon className="h-4 w-4" aria-hidden="true" />
                <span>RAM (GB) *</span>
              </div>
              <Input
                id="ram-gb"
                type="number"
                min="1"
                placeholder="64"
                value={ramGb}
                onChange={(e) => {
                  setRamGb(e.target.value)
                  if (hwFieldErrors.ram_gb) setHwFieldErrors((p) => ({ ...p, ram_gb: undefined }))
                }}
                error={hwFieldErrors.ram_gb}
                disabled={savingHardware}
                suffix="GB"
              />
            </div>

            {/* Almacenamiento */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm text-neutral-400">
                <ArchiveBoxIcon className="h-4 w-4" aria-hidden="true" />
                <span>Almacenamiento (GB) *</span>
              </div>
              <Input
                id="storage-gb"
                type="number"
                min="1"
                placeholder="2000"
                value={storageGb}
                onChange={(e) => {
                  setStorageGb(e.target.value)
                  if (hwFieldErrors.storage_gb) setHwFieldErrors((p) => ({ ...p, storage_gb: undefined }))
                }}
                error={hwFieldErrors.storage_gb}
                disabled={savingHardware}
                suffix="GB"
              />
            </div>
          </div>

          <Button
            variant="primary"
            loading={savingHardware}
            onClick={handleSaveHardware}
          >
            {savingHardware ? 'Guardando...' : 'Guardar hardware'}
          </Button>
        </div>
      </div>
    </div>
  )
}
