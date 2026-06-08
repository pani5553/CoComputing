import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import {
  BoltIcon,
  Bars3Icon,
  XMarkIcon,
  HomeIcon,
  BriefcaseIcon,
  WalletIcon,
  UserIcon,
  ArrowRightOnRectangleIcon,
  UserCircleIcon,
  CpuChipIcon,
  PlusCircleIcon,
} from '@heroicons/react/24/outline'
import { clsx } from 'clsx'
import { useAuth } from '../../hooks/useAuth'
import { RankBadge } from '../ui/Badge'

export default function Navbar() {
  const { provider, logout } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [dropdownOpen, setDropdownOpen] = useState(false)

  const navLinks = [
    { to: '/dashboard', label: 'Inicio', icon: HomeIcon },
    { to: '/tareas', label: 'Tareas', icon: BriefcaseIcon },
    { to: '/jobs', label: 'Mis trabajos', icon: CpuChipIcon },
    { to: '/cliente/mis-tareas', label: 'Publicar', icon: PlusCircleIcon },
    { to: '/cartera', label: 'Cartera', icon: WalletIcon },
    { to: '/perfil', label: 'Perfil', icon: UserIcon },
  ]

  return (
    <nav className="sticky top-0 z-30 bg-neutral-900 border-b border-neutral-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link
            to="/dashboard"
            className="flex items-center gap-2 text-brand-400 font-bold text-lg hover:text-brand-300 transition-colors"
          >
            <BoltIcon className="h-6 w-6" aria-hidden="true" />
            <span>Co-Computing</span>
          </Link>

          {/* Nav desktop */}
          <div className="hidden md:flex items-center gap-1">
            {navLinks.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  clsx(
                    'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150',
                    isActive
                      ? 'text-brand-400 font-semibold border-b-2 border-brand-400 rounded-none pb-[6px]'
                      : 'text-neutral-300 hover:text-neutral-100 hover:bg-neutral-800',
                  )
                }
              >
                {label}
              </NavLink>
            ))}
          </div>

          {/* Usuario desktop */}
          <div className="hidden md:flex items-center relative">
            <button
              onClick={() => setDropdownOpen((v) => !v)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-neutral-800 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500"
              aria-expanded={dropdownOpen}
              aria-haspopup="true"
            >
              {provider?.rank && <RankBadge rank={provider.rank} size="sm" />}
              <span className="text-sm font-medium text-neutral-200 max-w-[140px] truncate">
                {provider?.full_name ?? 'Usuario'}
              </span>
              <svg className="h-4 w-4 text-neutral-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {dropdownOpen && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setDropdownOpen(false)}
                  aria-hidden="true"
                />
                <div className="absolute right-0 top-full mt-2 w-48 bg-neutral-900 border border-neutral-700 rounded-xl shadow-xl shadow-black/40 z-20 py-1 animate-fade-in">
                  <Link
                    to="/perfil"
                    onClick={() => setDropdownOpen(false)}
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-neutral-300 hover:text-neutral-100 hover:bg-neutral-800 transition-colors"
                  >
                    <UserCircleIcon className="h-4 w-4" aria-hidden="true" />
                    Mi perfil
                  </Link>
                  <div className="border-t border-neutral-700 my-1" />
                  <button
                    onClick={() => {
                      setDropdownOpen(false)
                      logout()
                    }}
                    className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-danger-400 hover:text-danger-300 hover:bg-neutral-800 transition-colors"
                  >
                    <ArrowRightOnRectangleIcon className="h-4 w-4" aria-hidden="true" />
                    Cerrar sesión
                  </button>
                </div>
              </>
            )}
          </div>

          {/* Botón hamburguesa mobile */}
          <button
            className="md:hidden p-2 rounded-lg text-neutral-400 hover:text-neutral-100 hover:bg-neutral-800 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500"
            onClick={() => setMobileOpen((v) => !v)}
            aria-expanded={mobileOpen}
            aria-label={mobileOpen ? 'Cerrar menú' : 'Abrir menú'}
          >
            {mobileOpen ? (
              <XMarkIcon className="h-6 w-6" />
            ) : (
              <Bars3Icon className="h-6 w-6" />
            )}
          </button>
        </div>
      </div>

      {/* Menú mobile */}
      {mobileOpen && (
        <div className="md:hidden bg-neutral-900 border-b border-neutral-700 animate-fade-in">
          {/* Info usuario */}
          <div className="px-4 py-3 border-b border-neutral-800">
            <div className="flex items-center gap-2">
              {provider?.rank && <RankBadge rank={provider.rank} size="sm" />}
              <span className="text-sm font-semibold text-neutral-200">
                {provider?.full_name ?? 'Usuario'}
              </span>
            </div>
          </div>

          {/* Links */}
          <div className="px-3 py-2 space-y-1">
            {navLinks.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150',
                    isActive
                      ? 'bg-neutral-800 text-brand-400'
                      : 'text-neutral-300 hover:text-neutral-100 hover:bg-neutral-800',
                  )
                }
              >
                <Icon className="h-5 w-5" aria-hidden="true" />
                {label}
              </NavLink>
            ))}
          </div>

          <div className="px-3 py-2 border-t border-neutral-800">
            <button
              onClick={() => {
                setMobileOpen(false)
                logout()
              }}
              className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-danger-400 hover:text-danger-300 hover:bg-neutral-800 transition-colors"
            >
              <ArrowRightOnRectangleIcon className="h-5 w-5" aria-hidden="true" />
              Cerrar sesión
            </button>
          </div>
        </div>
      )}
    </nav>
  )
}
