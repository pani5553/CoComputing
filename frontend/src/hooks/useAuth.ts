import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import type { LoginRequest, Provider, RegisterRequest } from '../types'
import * as authApi from '../api/auth'

export function useAuth() {
  const { token, provider, isAuthenticated, login, logout, updateProvider } = useAuthStore()
  const navigate = useNavigate()

  const handleLogin = useCallback(
    async (data: LoginRequest): Promise<void> => {
      const response = await authApi.login(data)
      login(response.access_token, response.provider)
      navigate('/dashboard', { replace: true })
    },
    [login, navigate],
  )

  const handleRegister = useCallback(
    async (data: RegisterRequest): Promise<Provider> => {
      const provider = await authApi.register(data)
      // Después del registro, hace login automático
      const loginResponse = await authApi.login({
        email: data.email,
        password: data.password,
      })
      login(loginResponse.access_token, loginResponse.provider)
      navigate('/dashboard', { replace: true })
      return provider
    },
    [login, navigate],
  )

  const handleLogout = useCallback(() => {
    logout()
    navigate('/login', { replace: true })
  }, [logout, navigate])

  const refreshMe = useCallback(async () => {
    try {
      const me = await authApi.getMe()
      updateProvider(me)
      return me
    } catch {
      // Si el token ya no es válido, el interceptor se encargará de redirigir
      return null
    }
  }, [updateProvider])

  return {
    token,
    provider,
    isAuthenticated,
    login: handleLogin,
    register: handleRegister,
    logout: handleLogout,
    refreshMe,
    updateProvider,
  }
}
