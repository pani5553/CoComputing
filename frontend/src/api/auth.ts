import { apiClient } from './client'
import type { LoginRequest, LoginResponse, Provider, RegisterRequest } from '../types'

export async function register(data: RegisterRequest): Promise<Provider> {
  const response = await apiClient.post<Provider>('/auth/register', data)
  return response.data
}

export async function login(data: LoginRequest): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>('/auth/login', data)
  return response.data
}

export async function getMe(): Promise<Provider> {
  const response = await apiClient.get<Provider>('/auth/me')
  return response.data
}
