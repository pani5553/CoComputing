import { create } from 'zustand'
import { createJob as apiCreateJob, getJobs as apiGetJobs, getJob as apiGetJob } from '../api/compute'
import { extractErrorMessage } from '../api/client'
import type { Job, JobOperation } from '../types/compute'

interface JobState {
  jobs: Job[]
  currentJob: Job | null
  loading: boolean
  error: string | null

  fetchJobs: (status?: string) => Promise<void>
  fetchJob: (id: string) => Promise<void>
  createJob: (
    jobType: 'data-processing',
    operation: JobOperation,
    columns: string[],
    file?: File,
    embeddedData?: unknown[][],
    embeddedColumns?: string[],
  ) => Promise<Job>
  clearError: () => void
}

export const useJobStore = create<JobState>((set) => ({
  jobs: [],
  currentJob: null,
  loading: false,
  error: null,

  fetchJobs: async (status?: string) => {
    set({ loading: true, error: null })
    try {
      const jobs = await apiGetJobs(status)
      set({ jobs, loading: false })
    } catch (err) {
      set({ error: extractErrorMessage(err), loading: false })
    }
  },

  fetchJob: async (id: string) => {
    set({ loading: true, error: null })
    try {
      const job = await apiGetJob(id)
      set({ currentJob: job, loading: false })
    } catch (err) {
      set({ error: extractErrorMessage(err), loading: false })
    }
  },

  createJob: async (
    jobType,
    operation,
    columns,
    file,
    embeddedData,
    embeddedColumns,
  ) => {
    set({ loading: true, error: null })
    try {
      const params: Record<string, unknown> = { operation, columns }
      if (!file && embeddedData && embeddedColumns) {
        params['data'] = embeddedData
        params['columns'] = embeddedColumns
      }
      const job = await apiCreateJob(jobType, params, file)
      set((state) => ({ jobs: [job, ...state.jobs], loading: false }))
      return job
    } catch (err) {
      const message = extractErrorMessage(err)
      set({ error: message, loading: false })
      throw new Error(message)
    }
  },

  clearError: () => set({ error: null }),
}))
