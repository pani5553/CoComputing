import { apiClient } from './client'
import type {
  HardwareUpdateRequest,
  HardwareUpdateResponse,
  NameUpdateResponse,
  OnlineStatusResponse,
  ProfileStats,
} from '../types'

export async function getStats(): Promise<ProfileStats> {
  const response = await apiClient.get<ProfileStats>('/profile/stats')
  return response.data
}

export async function updateHardware(data: HardwareUpdateRequest): Promise<HardwareUpdateResponse> {
  const response = await apiClient.put<HardwareUpdateResponse>('/profile/hardware', data)
  return response.data
}

export async function setOnline(isOnline: boolean): Promise<OnlineStatusResponse> {
  const response = await apiClient.patch<OnlineStatusResponse>('/profile/online', {
    is_online: isOnline,
  })
  return response.data
}

export async function updateName(fullName: string): Promise<NameUpdateResponse> {
  const response = await apiClient.patch<NameUpdateResponse>('/profile/name', {
    full_name: fullName,
  })
  return response.data
}
