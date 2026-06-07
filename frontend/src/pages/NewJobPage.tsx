import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeftIcon,
  ArrowRightIcon,
  CloudArrowUpIcon,
  DocumentTextIcon,
  CheckIcon,
} from '@heroicons/react/24/outline'
import { useJobStore } from '../store/jobStore'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import ErrorAlert from '../components/ui/ErrorAlert'
import type { JobOperation } from '../types/compute'

// ─── Constantes ───────────────────────────────────────────────────────────────

const OPERATIONS: { value: JobOperation; label: string; description: string }[] = [
  { value: 'mean', label: 'Media', description: 'Promedio de los valores numéricos' },
  { value: 'sum', label: 'Suma', description: 'Suma total de los valores numéricos' },
  { value: 'min', label: 'Mínimo', description: 'Valor mínimo por columna' },
  { value: 'max', label: 'Máximo', description: 'Valor máximo por columna' },
  { value: 'count', label: 'Conteo', description: 'Número de filas no nulas por columna' },
]

const CHUNK_SIZE = 500
const REWARD_PER_CHUNK = 0.1

// ─── Datos de prueba ──────────────────────────────────────────────────────────

function generateSampleData(): { rows: string[][]; columns: string[] } {
  const columns = ['precio', 'cantidad', 'descuento', 'puntuacion']
  const rows: string[][] = []
  for (let i = 0; i < 1000; i++) {
    rows.push([
      (Math.random() * 1000).toFixed(2),
      String(Math.floor(Math.random() * 100) + 1),
      (Math.random() * 50).toFixed(2),
      (Math.random() * 10).toFixed(1),
    ])
  }
  return { rows, columns }
}

function parseCsvText(text: string): { rows: string[][]; columns: string[] } | null {
  const lines = text.trim().split('\n').filter((l) => l.trim())
  if (lines.length < 2) return null
  const columns = lines[0].split(',').map((c) => c.trim().replace(/^"|"$/g, ''))
  const rows = lines.slice(1).map((line) =>
    line.split(',').map((c) => c.trim().replace(/^"|"$/g, '')),
  )
  return { rows, columns }
}

// ─── Componente ───────────────────────────────────────────────────────────────

export default function NewJobPage() {
  const navigate = useNavigate()
  const { createJob, loading, error, clearError } = useJobStore()

  const [step, setStep] = useState<1 | 2>(1)

  // Paso 1: datos
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [parsedColumns, setParsedColumns] = useState<string[]>([])
  const [parsedRows, setParsedRows] = useState<string[][]>([])
  const [usingEmbedded, setUsingEmbedded] = useState(false)
  const [fileError, setFileError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Paso 2: operación
  const [operation, setOperation] = useState<JobOperation>('mean')
  const [selectedColumns, setSelectedColumns] = useState<string[]>([])
  const [columnError, setColumnError] = useState<string | null>(null)

  // ─── Handlers paso 1 ────────────────────────────────────────────────────────

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null
    setFileError(null)
    clearError()
    if (!file) return

    if (file.size > 10 * 1024 * 1024) {
      setFileError('El archivo no puede superar 10 MB.')
      return
    }
    if (!file.name.endsWith('.csv')) {
      setFileError('Solo se aceptan archivos .csv.')
      return
    }

    const reader = new FileReader()
    reader.onload = (ev) => {
      const text = ev.target?.result as string
      const parsed = parseCsvText(text)
      if (!parsed || parsed.columns.length === 0) {
        setFileError('El CSV no contiene columnas válidas.')
        return
      }
      setCsvFile(file)
      setParsedColumns(parsed.columns)
      setParsedRows(parsed.rows)
      setUsingEmbedded(false)
      setSelectedColumns(parsed.columns)
    }
    reader.readAsText(file)
  }, [clearError])

  const handleUseSampleData = useCallback(() => {
    const { rows, columns } = generateSampleData()
    setCsvFile(null)
    setParsedColumns(columns)
    setParsedRows(rows)
    setUsingEmbedded(true)
    setFileError(null)
    setSelectedColumns(columns)
    clearError()
    if (fileInputRef.current) fileInputRef.current.value = ''
  }, [clearError])

  // ─── Handlers paso 2 ────────────────────────────────────────────────────────

  const toggleColumn = useCallback((col: string) => {
    setSelectedColumns((prev) =>
      prev.includes(col) ? prev.filter((c) => c !== col) : [...prev, col],
    )
    setColumnError(null)
  }, [])

  // ─── Envío ────────────────────────────────────────────────────────────────────

  const estimatedChunks = parsedRows.length > 0
    ? Math.ceil(parsedRows.length / CHUNK_SIZE)
    : 0
  const estimatedReward = estimatedChunks * REWARD_PER_CHUNK

  async function handleSubmit() {
    if (selectedColumns.length === 0) {
      setColumnError('Selecciona al menos una columna.')
      return
    }
    clearError()

    try {
      if (usingEmbedded) {
        // Variante A: datos embebidos
        await createJob(
          'data-processing',
          operation,
          selectedColumns,
          undefined,
          parsedRows as unknown as unknown[][],
          parsedColumns,
        )
      } else if (csvFile) {
        // Variante B: multipart
        await createJob('data-processing', operation, selectedColumns, csvFile)
      } else {
        return
      }
      navigate('/jobs', {
        state: { toast: 'Trabajo enviado correctamente. Procesando...' },
      })
    } catch {
      // El error ya está en el store
    }
  }

  const canProceedStep1 = parsedColumns.length > 0 && !fileError

  // ─── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="animate-fade-in max-w-2xl space-y-6">
      {/* Cabecera */}
      <div>
        <button
          onClick={() => navigate('/jobs')}
          className="flex items-center gap-1.5 text-sm text-neutral-400 hover:text-neutral-200 transition-colors mb-3"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          Mis trabajos
        </button>
        <h1 className="text-2xl font-bold text-neutral-100">Nuevo trabajo</h1>
        <p className="text-sm text-neutral-500 mt-1">
          Sube un CSV o usa datos de prueba para distribuir el cómputo en la red.
        </p>
      </div>

      {/* Stepper indicador */}
      <div className="flex items-center gap-3">
        {([1, 2] as const).map((s, i) => (
          <div key={s} className="flex items-center gap-3">
            <div
              className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold border transition-colors ${
                step === s
                  ? 'bg-brand-600 border-brand-600 text-white'
                  : step > s
                  ? 'bg-success-600 border-success-600 text-white'
                  : 'bg-neutral-800 border-neutral-700 text-neutral-500'
              }`}
            >
              {step > s ? <CheckIcon className="h-3.5 w-3.5" /> : s}
            </div>
            <span
              className={`text-sm font-medium ${
                step === s ? 'text-neutral-100' : 'text-neutral-500'
              }`}
            >
              {s === 1 ? 'Datos' : 'Operación'}
            </span>
            {i < 1 && <div className="flex-1 h-px bg-neutral-700 w-8" />}
          </div>
        ))}
      </div>

      {/* Error global */}
      {error && <ErrorAlert message={error} onRetry={clearError} />}

      {/* ── PASO 1 ────────────────────────────────────────────────────────── */}
      {step === 1 && (
        <Card padding="lg" className="space-y-5">
          <h2 className="text-base font-semibold text-neutral-200">Fuente de datos</h2>

          {/* Drop zone CSV */}
          <div>
            <label className="block text-sm font-medium text-neutral-300 mb-2">
              Subir archivo CSV
            </label>
            <label
              htmlFor="csv-upload"
              className={`flex flex-col items-center justify-center gap-3 p-8 rounded-lg border-2 border-dashed cursor-pointer transition-colors ${
                csvFile
                  ? 'border-success-500/60 bg-success-900/10'
                  : 'border-neutral-700 hover:border-brand-500/60 bg-neutral-800/40 hover:bg-neutral-800/70'
              }`}
            >
              {csvFile ? (
                <>
                  <DocumentTextIcon className="h-8 w-8 text-success-400" />
                  <div className="text-center">
                    <p className="text-sm font-medium text-success-300">{csvFile.name}</p>
                    <p className="text-xs text-neutral-500 mt-0.5">
                      {parsedRows.length.toLocaleString('es-ES')} filas — {parsedColumns.length} columnas
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <CloudArrowUpIcon className="h-8 w-8 text-neutral-500" />
                  <div className="text-center">
                    <p className="text-sm text-neutral-400">
                      Arrastra un CSV o{' '}
                      <span className="text-brand-400 font-medium">busca un archivo</span>
                    </p>
                    <p className="text-xs text-neutral-600 mt-0.5">Máximo 10 MB · Solo .csv</p>
                  </div>
                </>
              )}
              <input
                id="csv-upload"
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="sr-only"
                onChange={handleFileChange}
              />
            </label>
            {fileError && (
              <p className="mt-1.5 text-xs text-danger-500">{fileError}</p>
            )}
          </div>

          {/* Separador */}
          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-neutral-800" />
            <span className="text-xs text-neutral-600 uppercase tracking-wide">o</span>
            <div className="flex-1 h-px bg-neutral-800" />
          </div>

          {/* Datos de prueba */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded-lg bg-neutral-800 border border-neutral-700">
            <div>
              <p className="text-sm font-medium text-neutral-200">Usar datos de prueba</p>
              <p className="text-xs text-neutral-500 mt-0.5">
                1.000 filas ficticias con columnas: precio, cantidad, descuento, puntuacion
              </p>
            </div>
            <Button
              variant={usingEmbedded ? 'secondary' : 'ghost'}
              size="sm"
              onClick={handleUseSampleData}
            >
              {usingEmbedded ? (
                <>
                  <CheckIcon className="h-3.5 w-3.5" />
                  Usando datos de prueba
                </>
              ) : (
                'Usar datos de prueba'
              )}
            </Button>
          </div>

          {/* Columnas detectadas */}
          {parsedColumns.length > 0 && (
            <div className="p-4 rounded-lg bg-neutral-800/60 border border-neutral-700">
              <p className="text-xs font-semibold text-neutral-400 uppercase tracking-wide mb-2">
                Columnas detectadas
              </p>
              <div className="flex flex-wrap gap-2">
                {parsedColumns.map((col) => (
                  <span
                    key={col}
                    className="px-2.5 py-1 rounded bg-neutral-700 text-neutral-200 text-xs font-mono"
                  >
                    {col}
                  </span>
                ))}
              </div>
              <p className="text-xs text-neutral-500 mt-2">
                {parsedRows.length.toLocaleString('es-ES')} filas &middot; se crearán{' '}
                <span className="text-neutral-300 font-medium">{estimatedChunks}</span>{' '}
                chunks de ~500 filas
              </p>
            </div>
          )}

          <div className="flex justify-end pt-2">
            <Button
              variant="primary"
              disabled={!canProceedStep1}
              onClick={() => setStep(2)}
              leftIcon={<ArrowRightIcon className="h-4 w-4" />}
            >
              Siguiente: elegir operación
            </Button>
          </div>
        </Card>
      )}

      {/* ── PASO 2 ────────────────────────────────────────────────────────── */}
      {step === 2 && (
        <Card padding="lg" className="space-y-6">
          <h2 className="text-base font-semibold text-neutral-200">Operación y columnas</h2>

          {/* Selección de operación */}
          <div>
            <p className="text-sm font-medium text-neutral-300 mb-3">Operación a aplicar</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {OPERATIONS.map(({ value, label, description }) => (
                <label
                  key={value}
                  className={`flex items-start gap-3 p-4 rounded-lg border cursor-pointer transition-colors ${
                    operation === value
                      ? 'border-brand-500/70 bg-brand-900/20'
                      : 'border-neutral-700 bg-neutral-800/40 hover:border-neutral-600'
                  }`}
                >
                  <input
                    type="radio"
                    name="operation"
                    value={value}
                    checked={operation === value}
                    onChange={() => setOperation(value)}
                    className="mt-0.5 accent-brand-500"
                  />
                  <div>
                    <p className="text-sm font-semibold text-neutral-200">{label}</p>
                    <p className="text-xs text-neutral-500 mt-0.5">{description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Selección de columnas */}
          <div>
            <p className="text-sm font-medium text-neutral-300 mb-1">
              Columnas a procesar
            </p>
            <p className="text-xs text-neutral-500 mb-3">
              Selecciona las columnas sobre las que se aplicará la operación.
            </p>
            <div className="flex flex-wrap gap-2">
              {parsedColumns.map((col) => {
                const checked = selectedColumns.includes(col)
                return (
                  <label
                    key={col}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border cursor-pointer text-sm transition-colors ${
                      checked
                        ? 'border-brand-500/70 bg-brand-900/20 text-brand-300'
                        : 'border-neutral-700 bg-neutral-800 text-neutral-400 hover:border-neutral-600'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleColumn(col)}
                      className="accent-brand-500"
                    />
                    <span className="font-mono">{col}</span>
                  </label>
                )
              })}
            </div>
            {columnError && (
              <p className="mt-1.5 text-xs text-danger-500">{columnError}</p>
            )}
          </div>

          {/* Estimación de recompensa */}
          <div className="p-4 rounded-lg bg-neutral-800 border border-neutral-700 flex items-center justify-between">
            <div>
              <p className="text-xs text-neutral-500 uppercase tracking-wide font-medium">
                Recompensa estimada
              </p>
              <p className="text-sm text-neutral-400 mt-0.5">
                {estimatedChunks} chunks &times; 0,10 CC/chunk
              </p>
            </div>
            <p className="text-xl font-bold text-success-400 tabular-nums">
              {estimatedReward.toFixed(2)} CC
            </p>
          </div>

          {/* Acciones */}
          <div className="flex items-center justify-between pt-2">
            <Button variant="secondary" onClick={() => setStep(1)}>
              <ArrowLeftIcon className="h-4 w-4" />
              Atrás
            </Button>
            <Button
              variant="primary"
              loading={loading}
              onClick={handleSubmit}
              disabled={loading || selectedColumns.length === 0}
            >
              {loading ? 'Enviando...' : 'Enviar trabajo'}
            </Button>
          </div>
        </Card>
      )}
    </div>
  )
}
