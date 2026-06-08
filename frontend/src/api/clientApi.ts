import { apiClient } from './client'
import type {
  CancelTaskResponse,
  ClientTaskDetail,
  ClientTaskListResponse,
  CreateTaskRequest,
  CreateTaskResponse,
  DepositRequest,
  DepositResponse,
} from '../types'

export async function deposit(data: DepositRequest): Promise<DepositResponse> {
  const response = await apiClient.post<DepositResponse>('/client/deposit', data)
  return response.data
}

export async function createTask(data: CreateTaskRequest): Promise<CreateTaskResponse> {
  const response = await apiClient.post<CreateTaskResponse>('/client/tasks', data)
  return response.data
}

export async function getMyTasks(): Promise<ClientTaskListResponse> {
  const response = await apiClient.get<ClientTaskListResponse>('/client/tasks')
  return response.data
}

export async function getClientTaskDetail(taskId: string): Promise<ClientTaskDetail> {
  const response = await apiClient.get<ClientTaskDetail>(`/client/tasks/${taskId}`)
  return response.data
}

export async function cancelTask(taskId: string): Promise<CancelTaskResponse> {
  const response = await apiClient.post<CancelTaskResponse>(`/client/tasks/${taskId}/cancel`)
  return response.data
}
