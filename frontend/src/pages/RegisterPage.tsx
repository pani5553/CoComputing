import { useState, type FormEvent } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { BoltIcon, EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline'
import { useAuth } from '../hooks/useAuth'
import { useAuthStore } from '../store/authStore'
import { extractErrorMessage } from '../api/client'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import ErrorAlert from '../components/ui/ErrorAlert'

export default function RegisterPage() {
  const { register } = useAuth()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<{
    full_name?: string
    email?: string
    password?: string
  }>({})

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  function validate() {
    const errors: typeof fieldErrors = {}
    if (!fullName.trim()) errors.full_name = 'Este campo es obligatorio.'
    if (!email.trim()) errors.email = 'Este campo es obligatorio.'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = 'Introduce un email válido.'
    if (!password) errors.password = 'Este campo es obligatorio.'
    else if (password.length < 8) errors.password = 'Mínimo 8 caracteres.'
    return errors
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)

    const errors = validate()
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setLoading(true)
    try {
      await register({ full_name: fullName.trim(), email: email.trim(), password })
      // register hace login automático y redirige
    } catch (err) {
      setError(extractErrorMessage(err, 'No se pudo crear la cuenta. Inténtalo de nuevo.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-neutral-950 flex flex-col">
      {/* Cabecera pública */}
      <header className="border-b border-neutral-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center gap-2">
          <BoltIcon className="h-6 w-6 text-brand-400" aria-hidden="true" />
          <span className="text-brand-400 font-bold text-lg">Co-Computing</span>
        </div>
      </header>

      {/* Formulario centrado */}
      <div className="flex-1 flex items-center justify-center px-4 py-16">
        <div className="w-full max-w-md bg-neutral-900 rounded-xl border border-neutral-700 p-8 animate-fade-in">
          {/* Logo */}
          <div className="flex items-center gap-2 mb-6">
            <BoltIcon className="h-7 w-7 text-brand-400" aria-hidden="true" />
            <span className="text-brand-400 text-2xl font-bold">Co-Computing</span>
          </div>

          <div className="border-t border-neutral-700 mb-6" />

          <h1 className="text-2xl font-bold text-neutral-100 leading-tight">
            Crea tu cuenta
          </h1>
          <p className="text-sm text-neutral-500 mt-1 mb-6">
            Empieza a monetizar tu hardware hoy
          </p>

          {error && (
            <ErrorAlert message={error} className="mb-5" />
          )}

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <Input
              label="Nombre completo"
              id="full_name"
              type="text"
              placeholder="Tu nombre"
              value={fullName}
              onChange={(e) => {
                setFullName(e.target.value)
                if (fieldErrors.full_name) setFieldErrors((prev) => ({ ...prev, full_name: undefined }))
              }}
              error={fieldErrors.full_name}
              disabled={loading}
              autoComplete="name"
              autoFocus
            />

            <Input
              label="Correo electrónico"
              id="email"
              type="email"
              placeholder="tu@email.com"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value)
                if (fieldErrors.email) setFieldErrors((prev) => ({ ...prev, email: undefined }))
              }}
              error={fieldErrors.email}
              disabled={loading}
              autoComplete="email"
            />

            <Input
              label="Contraseña"
              id="password"
              type={showPassword ? 'text' : 'password'}
              placeholder="••••••••"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value)
                if (fieldErrors.password) setFieldErrors((prev) => ({ ...prev, password: undefined }))
              }}
              error={fieldErrors.password}
              helperText={!fieldErrors.password ? 'Mínimo 8 caracteres' : undefined}
              disabled={loading}
              autoComplete="new-password"
              rightElement={
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="text-neutral-500 hover:text-neutral-300 transition-colors focus:outline-none"
                  aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <EyeSlashIcon className="h-4 w-4" />
                  ) : (
                    <EyeIcon className="h-4 w-4" />
                  )}
                </button>
              }
            />

            <Button
              type="submit"
              variant="primary"
              loading={loading}
              className="w-full mt-2"
            >
              {loading ? 'Creando tu cuenta...' : 'Crear cuenta'}
            </Button>
          </form>

          <div className="border-t border-neutral-700 my-6" />

          <p className="text-sm text-neutral-500 text-center">
            ¿Ya tienes cuenta?{' '}
            <Link
              to="/login"
              className="text-brand-400 hover:text-brand-300 font-medium underline-offset-2 hover:underline transition-colors"
            >
              Inicia sesión
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
