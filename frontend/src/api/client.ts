import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
})

// Request interceptor: añade el JWT si existe
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('co_computing_token')
    if (token && config.headers) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => Promise.reject(error),
)

// Response interceptor: maneja 401 globalmente
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Limpia la sesión y redirige al login
      localStorage.removeItem('co_computing_token')
      localStorage.removeItem('co_computing_provider')
      // Evita import circular usando un evento personalizado
      window.dispatchEvent(
        new CustomEvent('co_computing:session_expired', {
          detail: { message: 'Tu sesión ha expirado. Inicia sesión de nuevo.' },
        }),
      )
    }
    return Promise.reject(error)
  },
)

/** Extrae el mensaje de error legible de una respuesta de API */
export function extractErrorMessage(error: unknown, fallback = 'Ha ocurrido un error inesperado.'): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data
    if (typeof data?.detail === 'string') return data.detail
    if (Array.isArray(data?.detail) && data.detail.length > 0) {
      return data.detail.map((d: { msg: string }) => d.msg).join(', ')
    }
    if (error.response?.status === 401) return 'No autenticado. Inicia sesión de nuevo.'
    if (error.response?.status === 403) return 'No tienes permiso para realizar esta acción.'
    if (error.response?.status === 404) return 'Recurso no encontrado.'
    if (error.response?.status === 500) return 'Error interno del servidor.'
    if (error.code === 'ERR_NETWORK') return 'No se puede conectar con el servidor. Comprueba tu conexión.'
    if (error.code === 'ECONNABORTED') return 'La solicitud tardó demasiado. Inténtalo de nuevo.'
  }
  return fallback
}
