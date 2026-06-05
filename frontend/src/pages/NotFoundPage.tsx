import { Link } from 'react-router-dom'
import { ExclamationCircleIcon } from '@heroicons/react/24/outline'
import { useAuthStore } from '../store/authStore'

export default function NotFoundPage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  return (
    <div className="min-h-screen bg-neutral-950 flex flex-col">
      <div className="flex-1 flex flex-col items-center justify-center gap-6 px-4 py-16 text-center">
        <ExclamationCircleIcon className="h-20 w-20 text-neutral-700" aria-hidden="true" />
        <div>
          <h1 className="text-2xl font-bold text-neutral-300">Página no encontrada</h1>
          <p className="text-sm text-neutral-500 mt-2">
            La dirección a la que intentas acceder no existe.
          </p>
        </div>
        <Link
          to={isAuthenticated ? '/dashboard' : '/login'}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white font-semibold text-sm transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 focus:ring-offset-neutral-950"
        >
          ← Volver al {isAuthenticated ? 'dashboard' : 'inicio'}
        </Link>
      </div>
    </div>
  )
}
