import { apiClient } from './client'
import type {
  TransactionsResponse,
  Wallet,
  WithdrawRequest,
  WithdrawResponse,
} from '../types'

export async function getWallet(): Promise<Wallet> {
  const response = await apiClient.get<Wallet>('/wallet/')
  return response.data
}

export async function getTransactions(limit = 50, offset = 0): Promise<TransactionsResponse> {
  const response = await apiClient.get<TransactionsResponse>('/wallet/transactions', {
    params: { limit, offset },
  })
  return response.data
}

export async function withdraw(data: WithdrawRequest): Promise<WithdrawResponse> {
  const response = await apiClient.post<WithdrawResponse>('/wallet/withdraw', data)
  return response.data
}
