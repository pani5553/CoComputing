import { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getProgress } from '../api/tasks'
import type { ProgressResponse } from '../types'
import { extractErrorMessage } from '../api/client'

const POLL_INTERVAL = 3000
const MAX_CONSECUTIVE_ERRORS = 3

interface UseProgressResult {
  progress: ProgressResponse | null
  loading: boolean
  error: string | null
  consecutiveErrors: number
  refetch: () => void
}

export function useProgress(assignmentId: string | undefined): UseProgressResult {
  const [progress, setProgress] = useState<ProgressResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [consecutiveErrors, setConsecutiveErrors] = useState(0)

  const navigate = useNavigate()
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const isMountedRef = useRef(true)
  const consecutiveErrorsRef = useRef(0)

  const fetchProgress = useCallback(async () => {
    if (!assignmentId) return

    try {
      const data = await getProgress(assignmentId)

      if (!isMountedRef.current) return

      setProgress(data)
      setError(null)
      consecutiveErrorsRef.current = 0
      setConsecutiveErrors(0)
      setLoading(false)

      // Detener polling si la tarea terminó y redirigir
      if (data.status === 'completada' || data.status === 'fallida') {
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
        // Redirigir al dashboard con estado de resultado
        navigate('/dashboard', {
          replace: true,
          state: {
            taskCompleted: data.status === 'completada',
            taskFailed: data.status === 'fallida',
            assignmentId,
          },
        })
      }
    } catch (err) {
      if (!isMountedRef.current) return

      consecutiveErrorsRef.current += 1
      setConsecutiveErrors(consecutiveErrorsRef.current)

      if (consecutiveErrorsRef.current >= MAX_CONSECUTIVE_ERRORS) {
        setError(extractErrorMessage(err, 'No se puede actualizar el progreso. Comprobando la conexión...'))
      }

      setLoading(false)
    }
  }, [assignmentId, navigate])

  // Carga inicial inmediata + arrancar polling
  useEffect(() => {
    isMountedRef.current = true

    if (!assignmentId) {
      setLoading(false)
      return
    }

    // Primera llamada inmediata
    fetchProgress()

    // Polling cada 3s
    intervalRef.current = setInterval(fetchProgress, POLL_INTERVAL)

    return () => {
      isMountedRef.current = false
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [assignmentId, fetchProgress])

  const refetch = useCallback(() => {
    setError(null)
    consecutiveErrorsRef.current = 0
    setConsecutiveErrors(0)
    fetchProgress()
  }, [fetchProgress])

  return { progress, loading, error, consecutiveErrors, refetch }
}
