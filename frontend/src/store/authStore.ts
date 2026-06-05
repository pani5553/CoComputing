import { create } from 'zustand'
import type { Provider } from '../types'

interface AuthState {
  token: string | null
  provider: Provider | null
  isAuthenticated: boolean
  login: (token: string, provider: Provider) => void
  logout: () => void
  updateProvider: (provider: Partial<Provider>) => void
}

const TOKEN_KEY = 'co_computing_token'
const PROVIDER_KEY = 'co_computing_provider'

function loadFromStorage(): { token: string | null; provider: Provider | null } {
  try {
    const token = localStorage.getItem(TOKEN_KEY)
    const providerStr = localStorage.getItem(PROVIDER_KEY)
    const provider = providerStr ? (JSON.parse(providerStr) as Provider) : null
    return { token, provider }
  } catch {
    return { token: null, provider: null }
  }
}

const { token: initialToken, provider: initialProvider } = loadFromStorage()

export const useAuthStore = create<AuthState>((set) => ({
  token: initialToken,
  provider: initialProvider,
  isAuthenticated: initialToken !== null && initialProvider !== null,

  login: (token, provider) => {
    localStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem(PROVIDER_KEY, JSON.stringify(provider))
    set({ token, provider, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(PROVIDER_KEY)
    set({ token: null, provider: null, isAuthenticated: false })
  },

  updateProvider: (partial) => {
    set((state) => {
      if (!state.provider) return state
      const updated = { ...state.provider, ...partial }
      localStorage.setItem(PROVIDER_KEY, JSON.stringify(updated))
      return { provider: updated }
    })
  },
}))
