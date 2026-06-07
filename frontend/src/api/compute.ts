import { apiClient } from './client'
import type { Job, JobListResponse, JobResultResponse } from '../types/compute'

/**
 * Crea un nuevo job de cómputo.
 * - Si se pasa un archivo File, usa multipart/form-data (Variante B).
 * - Si no hay archivo, usa JSON puro con datos embebidos en params (Variante A).
 */
export async function createJob(
  jobType: 'data-processing',
  params: Record<string, unknown>,
  file?: File,
): Promise<Job> {
  if (file) {
    const formData = new FormData()
    formData.append('job_type', jobType)
    formData.append('params', JSON.stringify(params))
    formData.append('file', file)
    const response = await apiClient.post<Job>('/jobs', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  }

  const response = await apiClient.post<Job>('/jobs', {
    job_type: jobType,
    params,
  })
  return response.data
}

/** Lista todos los jobs del proveedor autenticado. */
export async function getJobs(status?: string): Promise<Job[]> {
  const params: Record<string, string> = {}
  if (status) params['status'] = status
  const response = await apiClient.get<JobListResponse>('/jobs', { params })
  return response.data.jobs
}

/** Detalle de un job con progreso real. */
export async function getJob(jobId: string): Promise<Job> {
  const response = await apiClient.get<Job>(`/jobs/${jobId}`)
  return response.data
}

/** Resultado consolidado de un job completado. */
export async function getJobResult(jobId: string): Promise<JobResultResponse> {
  const response = await apiClient.get<JobResultResponse>(`/jobs/${jobId}/result`)
  return response.data
}
