import { Link, Navigate } from 'react-router-dom'
import {
  BoltIcon,
  CpuChipIcon,
  BanknotesIcon,
  ShieldCheckIcon,
  ArrowRightIcon,
  UserPlusIcon,
  RectangleGroupIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'
import { useAuthStore } from '../store/authStore'

export default function LandingPage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">

      {/* Navbar mínima */}
      <header className="sticky top-0 z-30 bg-neutral-950/90 backdrop-blur border-b border-neutral-800">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 text-brand-400 font-bold text-lg">
            <BoltIcon className="h-6 w-6" aria-hidden="true" />
            <span>Co-Computing</span>
          </div>
          <nav className="flex items-center gap-2">
            <Link
              to="/login"
              className="px-4 py-2 text-sm font-medium text-neutral-300 hover:text-neutral-100 transition-colors"
            >
              Iniciar sesión
            </Link>
            <Link
              to="/registro"
              className="px-4 py-2 text-sm font-semibold bg-brand-600 hover:bg-brand-500 text-white rounded-lg transition-colors"
            >
              Registrarse
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        {/* Fondo decorativo */}
        <div
          className="absolute inset-0 pointer-events-none"
          aria-hidden="true"
        >
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-brand-600/10 rounded-full blur-3xl" />
        </div>

        <div className="relative max-w-6xl mx-auto px-4 sm:px-6 pt-24 pb-28 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 mb-6 rounded-full border border-brand-500/30 bg-brand-500/10 text-brand-400 text-xs font-semibold uppercase tracking-wider">
            <BoltIcon className="h-3.5 w-3.5" aria-hidden="true" />
            Red de cómputo distribuido
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-neutral-100 mb-6">
            Monetiza tu{' '}
            <span className="text-brand-400">CPU y GPU</span>
            <br className="hidden sm:block" />
            {' '}mientras no las usas
          </h1>

          <p className="max-w-2xl mx-auto text-lg sm:text-xl text-neutral-400 mb-10">
            Conecta tu hardware a la red Co-Computing, procesa tareas reales y acumula
            créditos CC que puedes retirar en cualquier momento. Sin inversión, sin riesgos.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/registro"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-7 py-3.5 text-base font-semibold bg-brand-600 hover:bg-brand-500 text-white rounded-xl shadow-lg shadow-brand-500/20 hover:shadow-brand-500/30 transition-all"
            >
              <UserPlusIcon className="h-5 w-5" aria-hidden="true" />
              Empezar gratis
            </Link>
            <Link
              to="/login"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-7 py-3.5 text-base font-semibold border border-neutral-700 hover:border-neutral-500 text-neutral-300 hover:text-neutral-100 rounded-xl transition-all"
            >
              Ya tengo cuenta
              <ArrowRightIcon className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>

      {/* Stats rápidas */}
      <section className="border-y border-neutral-800 bg-neutral-900/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10 grid grid-cols-2 sm:grid-cols-4 gap-6 text-center">
          {[
            { value: '100%', label: 'Pago por tarea' },
            { value: 'CPU + GPU', label: 'Hardware compatible' },
            { value: '< 1 min', label: 'Tiempo de registro' },
            { value: 'Sin comisión', label: 'En pagos completados' },
          ].map(({ value, label }) => (
            <div key={label}>
              <p className="text-2xl font-extrabold text-brand-400">{value}</p>
              <p className="text-sm text-neutral-500 mt-1">{label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Cómo funciona */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-24">
        <div className="text-center mb-14">
          <h2 className="text-3xl sm:text-4xl font-bold text-neutral-100 mb-3">
            Cómo funciona
          </h2>
          <p className="text-neutral-400 max-w-xl mx-auto">
            En tres pasos ya estás generando ingresos pasivos con tu hardware.
          </p>
        </div>

        <div className="grid sm:grid-cols-3 gap-8">
          {[
            {
              step: '01',
              icon: <UserPlusIcon className="h-7 w-7" aria-hidden="true" />,
              title: 'Regístrate y configura',
              description:
                'Crea tu cuenta en menos de un minuto. Indica el hardware disponible (CPU, GPU, RAM) y tu perfil queda listo para recibir trabajo.',
            },
            {
              step: '02',
              icon: <CpuChipIcon className="h-7 w-7" aria-hidden="true" />,
              title: 'Procesa tareas reales',
              description:
                'Acepta tareas del catálogo: renderizado 3D, análisis de datos, entrenamiento ML. El worker ejecuta el cómputo y devuelve los resultados.',
            },
            {
              step: '03',
              icon: <BanknotesIcon className="h-7 w-7" aria-hidden="true" />,
              title: 'Cobra tus ganancias',
              description:
                'Cada tarea completada acredita CC en tu cartera de forma inmediata. Retira cuando quieras por PayPal, transferencia o cripto.',
            },
          ].map(({ step, icon, title, description }) => (
            <div
              key={step}
              className="relative bg-neutral-900 border border-neutral-800 rounded-2xl p-7 hover:border-neutral-600 transition-colors"
            >
              <div className="absolute top-5 right-6 text-4xl font-black text-neutral-800 select-none">
                {step}
              </div>
              <div className="inline-flex items-center justify-center h-12 w-12 rounded-xl bg-brand-600/15 text-brand-400 mb-5">
                {icon}
              </div>
              <h3 className="text-lg font-semibold text-neutral-100 mb-2">{title}</h3>
              <p className="text-sm text-neutral-400 leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Beneficios */}
      <section className="bg-neutral-900/40 border-t border-neutral-800">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-24">
          <div className="grid lg:grid-cols-2 gap-14 items-center">
            <div>
              <h2 className="text-3xl sm:text-4xl font-bold text-neutral-100 mb-5">
                Tu hardware trabaja.<br />
                <span className="text-brand-400">Tú cobras.</span>
              </h2>
              <p className="text-neutral-400 text-lg mb-8 leading-relaxed">
                La mayoría de los ordenadores están al 5% de su capacidad la mayor parte
                del día. Co-Computing convierte ese potencial desperdiciado en ingresos reales.
              </p>

              <ul className="space-y-4">
                {[
                  'Sin descargar software masivo — worker ligero en Python',
                  'Tú decides cuándo conectarte y cuánto hardware ofrecer',
                  'Sistema de reputación por confiabilidad y precisión',
                  'Pagos transparentes y auditables en tiempo real',
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <CheckCircleIcon className="h-5 w-5 text-brand-400 shrink-0 mt-0.5" aria-hidden="true" />
                    <span className="text-neutral-300 text-sm">{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {[
                {
                  icon: <RectangleGroupIcon className="h-6 w-6" aria-hidden="true" />,
                  title: 'GPU acelerada',
                  desc: 'Tareas de ML y renderizado usan tu GPU al máximo rendimiento.',
                },
                {
                  icon: <CpuChipIcon className="h-6 w-6" aria-hidden="true" />,
                  title: 'CPU multihilo',
                  desc: 'Análisis de datos y simulaciones aprovechan todos tus núcleos.',
                },
                {
                  icon: <ShieldCheckIcon className="h-6 w-6" aria-hidden="true" />,
                  title: 'Consenso distribuido',
                  desc: 'Varios proveedores validan el mismo resultado para garantizar precisión.',
                },
                {
                  icon: <BanknotesIcon className="h-6 w-6" aria-hidden="true" />,
                  title: 'Escrow seguro',
                  desc: 'Los fondos del cliente se bloquean antes de empezar. Cobras al terminar.',
                },
              ].map(({ icon, title, desc }) => (
                <div
                  key={title}
                  className="bg-neutral-900 border border-neutral-800 rounded-xl p-5"
                >
                  <div className="text-brand-400 mb-3">{icon}</div>
                  <h4 className="text-sm font-semibold text-neutral-100 mb-1">{title}</h4>
                  <p className="text-xs text-neutral-500 leading-relaxed">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA final */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-24 text-center">
        <div className="bg-gradient-to-br from-brand-600/20 to-brand-700/5 border border-brand-600/30 rounded-3xl px-6 py-16">
          <BoltIcon className="h-12 w-12 text-brand-400 mx-auto mb-6" aria-hidden="true" />
          <h2 className="text-3xl sm:text-4xl font-bold text-neutral-100 mb-4">
            ¿Listo para empezar?
          </h2>
          <p className="text-neutral-400 text-lg mb-10 max-w-xl mx-auto">
            Únete a la red de cómputo distribuido. Registro gratuito, sin tarjeta de crédito.
          </p>
          <Link
            to="/registro"
            className="inline-flex items-center gap-2 px-8 py-4 text-base font-semibold bg-brand-600 hover:bg-brand-500 text-white rounded-xl shadow-lg shadow-brand-500/25 hover:shadow-brand-500/40 transition-all"
          >
            <UserPlusIcon className="h-5 w-5" aria-hidden="true" />
            Crear cuenta gratis
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-neutral-800 bg-neutral-950">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-neutral-600">
          <div className="flex items-center gap-2">
            <BoltIcon className="h-4 w-4 text-brand-600" aria-hidden="true" />
            <span className="font-semibold text-neutral-500">Co-Computing</span>
          </div>
          <p>Plataforma de cómputo distribuido · {new Date().getFullYear()}</p>
          <div className="flex items-center gap-4">
            <Link to="/login" className="hover:text-neutral-400 transition-colors">
              Iniciar sesión
            </Link>
            <Link to="/registro" className="hover:text-neutral-400 transition-colors">
              Registrarse
            </Link>
          </div>
        </div>
      </footer>

    </div>
  )
}
