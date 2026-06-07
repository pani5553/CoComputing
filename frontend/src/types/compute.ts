// ─── Job ──────────────────────────────────────────────────────────────────────

export type JobStatus =
  | 'pending'
  | 'splitting'
  | 'processing'
  | 'validating'
  | 'completed'
  | 'failed'

export type ChunkStatus = 'pending' | 'assigned' | 'done' | 'rejected'

export interface Job {
  id: string
  client_id: string
  job_type: string
  status: JobStatus
  params: Record<string, unknown>
  total_chunks: number
  completed_chunks: number
  reward_total: number
  result: Record<string, unknown> | null
  created_at: string       // ISO 8601 UTC
  completed_at: string | null
  progress: number         // 0–100, calculado por el backend
}

export interface JobListResponse {
  count: number
  jobs: Job[]
}

// ─── Chunks ───────────────────────────────────────────────────────────────────

export interface ChunkWithPayload {
  chunk_id: string
  job_id: string
  chunk_index: number
  job_type: string
  payload: Record<string, unknown>
}

export interface ClaimResponse {
  chunks: ChunkWithPayload[]
}

// ─── Submit ───────────────────────────────────────────────────────────────────

export interface SubmitRequest {
  result: Record<string, unknown>
  duration_ms: number
}

export interface SubmitResponse {
  chunk_result_id: string
  chunk_id: string
  status: ChunkStatus
  message: string
}

// ─── Create ───────────────────────────────────────────────────────────────────

export type JobOperation = 'mean' | 'sum' | 'min' | 'max' | 'count'

export interface JobCreateRequest {
  job_type: 'data-processing'
  params: {
    operation: JobOperation
    columns?: string[]
  }
}

// ─── Result ───────────────────────────────────────────────────────────────────

export interface JobResultResponse {
  id: string
  status: JobStatus
  result: Record<string, unknown>
  total_chunks: number
  completed_chunks: number
  completed_at: string
}
