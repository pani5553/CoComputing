// ─── Rangos ───────────────────────────────────────────────────────────────────
export type Rank = 'nuevo' | 'confiable' | 'experto' | 'elite'

// ─── Proveedor ────────────────────────────────────────────────────────────────
export interface Provider {
  id: string
  full_name: string
  email: string
  trust_score: number
  rank: Rank
  tasks_completed: number
  success_rate: number
  total_earned: number
  is_online: boolean
  cpu_model?: string | null
  gpu_model?: string | null
  ram_gb?: number | null
  storage_gb?: number | null
  completion_rate?: number
  accuracy?: number
  response_time_score?: number
  client_rating?: number
  created_at: string
  updated_at?: string
}

// ─── Auth ─────────────────────────────────────────────────────────────────────
export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  full_name: string
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  provider: Provider
}

// ─── Tareas ───────────────────────────────────────────────────────────────────
export type TaskType =
  | 'renderizado_3d'
  | 'entrenamiento_ml'
  | 'transcodificacion_video'
  | 'analisis_datos'
  | 'simulacion_fisica'

export type Difficulty = 'facil' | 'medio' | 'dificil'

export type HardwareRequired = 'cpu' | 'gpu' | 'mixto'

export type TaskStatus = 'disponible' | 'en_progreso' | 'completada' | 'cancelada'

export interface ActiveAssignment {
  id: string
  status: AssignmentStatus
  accepted_at: string
  started_at: string | null
}

export interface Task {
  id: string
  title: string
  task_type: TaskType
  description: string
  reward: number
  duration_min: number
  duration_max: number
  difficulty: Difficulty
  hardware_required: HardwareRequired
  total_slots: number
  slots_left: number
  stages: string[]
  requester_name: string
  status: TaskStatus
  created_at: string
  active_assignment?: ActiveAssignment | null
}

export interface TasksResponse {
  count: number
  tasks: Task[]
}

export interface TaskFilters {
  difficulty?: string
  hardware?: string
  task_type?: string
  min_reward?: number
}

// ─── Asignaciones ─────────────────────────────────────────────────────────────
export type AssignmentStatus =
  | 'aceptada'
  | 'procesando'
  | 'completada'
  | 'fallida'
  | 'cancelada'

export interface Assignment {
  id: string
  task_id: string
  task_title?: string
  task_type?: TaskType
  provider_id?: string
  status: AssignmentStatus
  reward_paid: number | null
  trust_delta: number | null
  accepted_at: string
  started_at: string | null
  completed_at: string | null
}

export interface AssignmentsHistoryResponse {
  count: number
  assignments: Assignment[]
}

export interface StartTaskResponse {
  assignment_id: string
  task_id: string
  status: AssignmentStatus
  started_at: string
  stages: string[]
  stages_count: number
  duration_max_seconds: number
}

export interface CompleteTaskResponse {
  assignment_id: string
  task_id: string
  status: AssignmentStatus
  reward_paid: number
  trust_delta: number
  new_trust_score: number
  new_rank: Rank
  completed_at: string
}

export interface FailTaskResponse {
  assignment_id: string
  task_id: string
  status: AssignmentStatus
  reward_paid: null
  trust_delta: number
  new_trust_score: number
  new_rank: Rank
  completed_at: string
}

// ─── Progreso ─────────────────────────────────────────────────────────────────
export interface ProgressResponse {
  assignment_id: string
  task_id: string
  task_title: string
  status: AssignmentStatus
  progress: number
  current_stage_index: number
  stages: string[]
  started_at: string | null
  can_complete: boolean
}

// ─── Cartera ──────────────────────────────────────────────────────────────────
export interface Wallet {
  id: string
  provider_id: string
  available_balance: number
  pending_balance: number
  total_earned: number
  total_withdrawn: number
  updated_at: string
}

export type TransactionType =
  | 'pago_tarea'
  | 'retiro'
  | 'bonus'
  | 'penalizacion'
  | 'deposito'
  | 'escrow'
  | 'reembolso'
  | 'pago_recibido'

export type TransactionStatus = 'completada' | 'pendiente' | 'cancelada'

export type WithdrawMethod = 'transferencia' | 'paypal' | 'cripto'

export interface Transaction {
  id: string
  provider_id: string
  task_id: string | null
  amount: number
  tx_type: TransactionType
  status: TransactionStatus
  description: string
  withdraw_method: WithdrawMethod | null
  withdraw_destination: string | null
  created_at: string
}

export interface TransactionsResponse {
  count: number
  total: number
  transactions: Transaction[]
}

export interface WithdrawRequest {
  amount: number
  method: WithdrawMethod
  destination: string
}

export interface WithdrawResponse {
  transaction_id: string
  amount: number
  method: WithdrawMethod
  destination: string
  status: TransactionStatus
  new_available_balance: number
  message: string
}

// ─── Perfil ───────────────────────────────────────────────────────────────────
export interface TrustScoreDetail {
  completion_rate: number
  completion_rate_weight: number
  accuracy: number
  accuracy_weight: number
  response_time_score: number
  response_time_weight: number
  client_rating: number
  client_rating_weight: number
}

export interface RankInfo {
  current_rank: Rank
  current_rank_min: number
  current_rank_max: number
  next_rank: Rank | null
  next_rank_min: number | null
  points_to_next_rank: number | null
}

export interface HardwareInfo {
  cpu_model: string | null
  gpu_model: string | null
  ram_gb: number | null
  storage_gb: number | null
}

export interface ProfileStats extends Provider {
  trust_score_detail: TrustScoreDetail
  rank_info: RankInfo
  hardware: HardwareInfo
}

export interface HardwareUpdateRequest {
  cpu_model: string
  gpu_model: string | null
  ram_gb: number
  storage_gb: number
}

export interface HardwareUpdateResponse {
  cpu_model: string | null
  gpu_model: string | null
  ram_gb: number | null
  storage_gb: number | null
  updated_at: string
}

export interface OnlineStatusResponse {
  is_online: boolean
  updated_at: string
}

export interface NameUpdateResponse {
  full_name: string
  updated_at: string
}

// ─── Lado cliente ─────────────────────────────────────────────────────────────

export interface DepositRequest {
  amount: number
}

export interface DepositResponse {
  transaction_id: string
  amount: number
  new_available_balance: number
  message: string
}

export interface CreateTaskRequest {
  title: string
  task_type: TaskType
  description: string
  reward: number
  difficulty: Difficulty
  hardware_required: HardwareRequired
  total_slots: number
  duration_min: number
  duration_max: number
  stages: string[]
  requester_name: string
}

export interface CreateTaskResponse {
  task_id: string
  title: string
  reward: number
  total_slots: number
  escrow_total: number
  new_available_balance: number
  message: string
}

export interface ClientTaskSummary {
  id: string
  title: string
  task_type: TaskType
  reward: number
  total_slots: number
  slots_left: number
  slots_completed: number
  status: TaskStatus
  escrow_held: number
  escrow_released: number
  created_at: string
}

export interface ClientTaskListResponse {
  count: number
  tasks: ClientTaskSummary[]
}

export interface AssignmentInfo {
  id: string
  provider_id: string
  provider_name: string
  status: AssignmentStatus
  reward_paid: number | null
  accepted_at: string
  completed_at: string | null
}

export interface ClientTaskDetail {
  id: string
  title: string
  task_type: TaskType
  description: string
  reward: number
  difficulty: Difficulty
  hardware_required: HardwareRequired
  total_slots: number
  slots_left: number
  status: TaskStatus
  escrow_held: number
  escrow_released: number
  assignments: AssignmentInfo[]
  created_at: string
}

export interface CancelTaskResponse {
  task_id: string
  refund_amount: number
  new_available_balance: number
  message: string
}

// ─── Utiles ───────────────────────────────────────────────────────────────────
export interface ApiError {
  detail: string | Array<{ msg: string; loc: string[] }>
}
