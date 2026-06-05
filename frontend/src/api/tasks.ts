import { apiClient } from './client'
import type {
  Assignment,
  AssignmentsHistoryResponse,
  CompleteTaskResponse,
  FailTaskResponse,
  ProgressResponse,
  StartTaskResponse,
  Task,
  TaskFilters,
  TasksResponse,
} from '../types'

export async function getTasks(filters?: TaskFilters): Promise<TasksResponse> {
  const params: Record<string, string | number> = {}
  if (filters?.difficulty) params['difficulty'] = filters.difficulty
  if (filters?.hardware) params['hardware'] = filters.hardware
  if (filters?.task_type) params['task_type'] = filters.task_type
  if (filters?.min_reward !== undefined && filters.min_reward > 0) {
    params['min_reward'] = filters.min_reward
  }
  const response = await apiClient.get<TasksResponse>('/tasks/', { params })
  return response.data
}

export async function getTask(taskId: string): Promise<Task> {
  const response = await apiClient.get<Task>(`/tasks/${taskId}`)
  return response.data
}

export async function acceptTask(taskId: string): Promise<Assignment> {
  const response = await apiClient.post<Assignment>(`/tasks/${taskId}/accept`, {})
  return response.data
}

export async function startTask(taskId: string): Promise<StartTaskResponse> {
  const response = await apiClient.post<StartTaskResponse>(`/tasks/${taskId}/start`, {})
  return response.data
}

export async function completeTask(taskId: string): Promise<CompleteTaskResponse> {
  const response = await apiClient.post<CompleteTaskResponse>(`/tasks/${taskId}/complete`, {})
  return response.data
}

export async function failTask(taskId: string): Promise<FailTaskResponse> {
  const response = await apiClient.post<FailTaskResponse>(`/tasks/${taskId}/fail`, {})
  return response.data
}

export async function getProgress(assignmentId: string): Promise<ProgressResponse> {
  const response = await apiClient.get<ProgressResponse>(
    `/tasks/assignments/${assignmentId}/progress`,
  )
  return response.data
}

export async function getHistory(): Promise<AssignmentsHistoryResponse> {
  const response = await apiClient.get<AssignmentsHistoryResponse>('/tasks/my/history')
  return response.data
}
