import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BanknotesIcon,
  ClockIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  DocumentTextIcon,
  PlusIcon,
} from '@heroicons/react/24/outline'
import { getWallet, getTransactions, withdraw } from '../api/wallet'
import { extractErrorMessage } from '../api/client'
import type { Wallet, Transaction, TransactionType, WithdrawMethod } from '../types'
import { SkeletonStat, SkeletonRow } from '../components/ui/SkeletonCard'
import ErrorAlert from '../components/ui/ErrorAlert'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import Input from '../components/ui/Input'
import EmptyState from '../components/ui/EmptyState'
import {
  TransactionTypeBadge,
  TransactionStatusBadge,
} from '../components/ui/Badge'
import { formatCC, formatDateTime } from '../utils/format'

const PAGE_SIZE = 10

// Tipos de transacción que representan un ingreso (saldo entrante) para el proveedor.
// El backend siempre guarda `amount` como magnitud positiva (ver wallet_service.py /
// client_service.py): el signo +/- es puramente de presentación aquí. Mantener en sync
// con `TransactionType` (types/index.ts) y `txTypeConfig` (components/ui/Badge.tsx) —
// cualquier tipo nuevo debe añadirse explícitamente a una de las dos categorías.
const INCOME_TX_TYPES: readonly TransactionType[] = [
  'pago_tarea', // cobro por tarea completada
  'bonus', // bono
  'deposito', // recarga de saldo
  'reembolso', // devolución de escrow no usado
  'pago_recibido', // cobro recibido
]

export default function WalletPage() {
  const navigate = useNavigate()
  const [wallet, setWallet] = useState<Wallet | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [totalTx, setTotalTx] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [txLoading, setTxLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Modal de retiro
  const [withdrawOpen, setWithdrawOpen] = useState(false)
  const [withdrawStep, setWithdrawStep] = useState<1 | 2>(1)
  const [withdrawMethod, setWithdrawMethod] = useState<WithdrawMethod>('paypal')
  const [withdrawDest, setWithdrawDest] = useState('')
  const [withdrawAmount, setWithdrawAmount] = useState('')
  const [withdrawLoading, setWithdrawLoading] = useState(false)
  const [withdrawError, setWithdrawError] = useState<string | null>(null)
  const [withdrawSuccess, setWithdrawSuccess] = useState<string | null>(null)
  const [destError, setDestError] = useState<string | null>(null)
  const [amountError, setAmountError] = useState<string | null>(null)

  // Modal de añadir créditos (placeholder, sin funcionalidad real todavía)
  const [addCreditsOpen, setAddCreditsOpen] = useState(false)

  async function loadWallet() {
    setLoading(true)
    setError(null)
    try {
      const data = await getWallet()
      setWallet(data)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function loadTransactions(p = 0) {
    setTxLoading(true)
    try {
      const data = await getTransactions(PAGE_SIZE, p * PAGE_SIZE)
      setTransactions(data.transactions)
      setTotalTx(data.total)
      setPage(p)
    } catch {
      // No bloquear la UI por error de historial
    } finally {
      setTxLoading(false)
    }
  }

  useEffect(() => {
    loadWallet()
    loadTransactions(0)
  }, [])

  function openWithdrawModal() {
    setWithdrawStep(1)
    setWithdrawMethod('paypal')
    setWithdrawDest('')
    setWithdrawAmount('')
    setWithdrawError(null)
    setDestError(null)
    setAmountError(null)
    setWithdrawOpen(true)
  }

  function validateWithdraw(): boolean {
    let valid = true
    setDestError(null)
    setAmountError(null)

    if (!withdrawDest.trim()) {
      setDestError('Este campo es obligatorio.')
      valid = false
    }

    const amount = parseFloat(withdrawAmount.replace(',', '.'))
    if (isNaN(amount) || amount <= 0) {
      setAmountError('Introduce un monto válido.')
      valid = false
    } else if (amount < 10) {
      setAmountError('El monto mínimo de retiro es 10,00 CC.')
      valid = false
    } else if (wallet && amount > wallet.available_balance) {
      setAmountError(`El monto supera tu saldo disponible (${formatCC(wallet.available_balance)}).`)
      valid = false
    }
    return valid
  }

  function handleWithdrawNext() {
    if (!validateWithdraw()) return
    setWithdrawStep(2)
  }

  async function handleWithdrawConfirm() {
    setWithdrawError(null)
    setWithdrawLoading(true)
    try {
      const amount = parseFloat(withdrawAmount.replace(',', '.'))
      const result = await withdraw({
        amount,
        method: withdrawMethod,
        destination: withdrawDest.trim(),
      })
      setWithdrawOpen(false)
      setWithdrawSuccess(result.message)
      // Refrescar datos
      await loadWallet()
      await loadTransactions(0)
    } catch (err) {
      setWithdrawError(extractErrorMessage(err))
      setWithdrawStep(1)
    } finally {
      setWithdrawLoading(false)
    }
  }

  const methodLabels: Record<WithdrawMethod, string> = {
    transferencia: 'Transferencia bancaria',
    paypal: 'PayPal',
    cripto: 'Criptomoneda',
  }

  const destPlaceholders: Record<WithdrawMethod, string> = {
    transferencia: 'IBAN: ES12 3456...',
    paypal: 'tu@paypal.com',
    cripto: 'Dirección de wallet',
  }

  const totalPages = Math.ceil(totalTx / PAGE_SIZE)

  return (
    <div className="animate-fade-in space-y-8">
      <h1 className="text-2xl font-bold text-neutral-100">Mi cartera</h1>

      {/* Error principal */}
      {error && <ErrorAlert message={error} onRetry={loadWallet} />}

      {/* Mensaje de éxito retiro */}
      {withdrawSuccess && (
        <div className="flex items-start gap-3 p-4 rounded-lg bg-success-900/50 border border-success-500/30 text-success-300 text-sm" role="status">
          <p>{withdrawSuccess}</p>
        </div>
      )}

      {/* Tarjetas de saldo */}
      <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-5">
        <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-4">
          Saldos
        </h2>
        <div className="border-t border-neutral-700 pt-4">
          {loading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <SkeletonStat />
              <SkeletonStat />
              <SkeletonStat />
              <SkeletonStat />
            </div>
          ) : wallet ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
                {/* Disponible */}
                <div className="p-5 rounded-xl bg-neutral-900 border border-brand-500/30 shadow-lg shadow-brand-500/5">
                  <div className="flex items-center gap-2 mb-2">
                    <BanknotesIcon className="h-5 w-5 text-neutral-500" aria-hidden="true" />
                    <span className="text-xs text-neutral-500 uppercase tracking-wide">Disponible</span>
                  </div>
                  <p className="text-3xl font-bold text-success-400 tabular-nums">
                    {formatCC(wallet.available_balance)}
                  </p>
                  <p className="text-xs text-neutral-500 mt-1">Listo para retirar</p>
                </div>

                {/* Pendiente */}
                <div className="p-5 rounded-xl bg-neutral-900 border border-neutral-700">
                  <div className="flex items-center gap-2 mb-2">
                    <ClockIcon className="h-5 w-5 text-neutral-500" aria-hidden="true" />
                    <span className="text-xs text-neutral-500 uppercase tracking-wide">Pendiente</span>
                  </div>
                  <p className="text-2xl font-bold text-neutral-100 tabular-nums">
                    {formatCC(wallet.pending_balance)}
                  </p>
                  <p className="text-xs text-neutral-500 mt-1">En proceso</p>
                </div>

                {/* Total ganado */}
                <div className="p-5 rounded-xl bg-neutral-900 border border-neutral-700">
                  <div className="flex items-center gap-2 mb-2">
                    <ArrowUpIcon className="h-5 w-5 text-neutral-500" aria-hidden="true" />
                    <span className="text-xs text-neutral-500 uppercase tracking-wide">Total ganado</span>
                  </div>
                  <p className="text-2xl font-bold text-neutral-100 tabular-nums">
                    {formatCC(wallet.total_earned)}
                  </p>
                </div>

                {/* Total retirado */}
                <div className="p-5 rounded-xl bg-neutral-900 border border-neutral-700">
                  <div className="flex items-center gap-2 mb-2">
                    <ArrowDownIcon className="h-5 w-5 text-neutral-500" aria-hidden="true" />
                    <span className="text-xs text-neutral-500 uppercase tracking-wide">Total retirado</span>
                  </div>
                  <p className="text-2xl font-bold text-neutral-100 tabular-nums">
                    {formatCC(wallet.total_withdrawn)}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <Button
                  variant="primary"
                  onClick={openWithdrawModal}
                  disabled={wallet.available_balance < 10}
                >
                  Solicitar retiro
                </Button>
                <Button
                  variant="secondary"
                  leftIcon={<PlusIcon className="h-4 w-4" />}
                  onClick={() => setAddCreditsOpen(true)}
                >
                  Añadir créditos
                </Button>
                <p className="text-xs text-neutral-500">
                  Saldo mínimo para retirar: 10,00 CC
                </p>
              </div>
            </>
          ) : null}
        </div>
      </div>

      {/* Historial de transacciones */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-neutral-100">
            Historial de transacciones
          </h2>
          {totalTx > 0 && (
            <p className="text-sm text-neutral-500">{totalTx} transacciones</p>
          )}
        </div>

        {txLoading && transactions.length === 0 ? (
          <div className="w-full border border-neutral-700 rounded-xl overflow-hidden">
            <table className="w-full">
              <tbody>
                {Array.from({ length: 5 }).map((_, i) => (
                  <SkeletonRow key={i} />
                ))}
              </tbody>
            </table>
          </div>
        ) : transactions.length === 0 ? (
          <div className="bg-neutral-900 border border-neutral-700 rounded-xl">
            <EmptyState
              icon={<DocumentTextIcon className="h-12 w-12" />}
              title="No tienes transacciones aún."
              description="Cuando completes tu primera tarea, aparecerá aquí."
              action={{
                label: 'Explorar tareas disponibles',
                onClick: () => navigate('/tareas'),
              }}
              actionVariant="secondary"
            />
          </div>
        ) : (
          <>
            <div className="w-full border border-neutral-700 rounded-xl overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="bg-neutral-800 border-b border-neutral-700">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                      Fecha
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide hidden sm:table-cell">
                      Tipo
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                      Descripción
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                      Monto
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide hidden md:table-cell">
                      Estado
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((tx) => {
                    const isIncome = INCOME_TX_TYPES.includes(tx.tx_type)
                    return (
                      <tr
                        key={tx.id}
                        className="border-b border-neutral-800 last:border-0 hover:bg-neutral-800/50 transition-colors duration-100"
                      >
                        <td className="px-4 py-3.5 text-xs text-neutral-500 whitespace-nowrap">
                          {formatDateTime(tx.created_at)}
                        </td>
                        <td className="px-4 py-3.5 hidden sm:table-cell">
                          <TransactionTypeBadge type={tx.tx_type} />
                        </td>
                        <td className="px-4 py-3.5 text-sm text-neutral-300 max-w-[200px] truncate">
                          {tx.description}
                          {tx.withdraw_destination && (
                            <span className="block text-xs text-neutral-500 font-mono truncate">
                              {tx.withdraw_destination}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3.5 text-right">
                          <span
                            className={`text-sm font-semibold tabular-nums ${
                              isIncome ? 'text-success-400' : 'text-danger-400'
                            }`}
                          >
                            {isIncome ? '+' : '-'}{formatCC(tx.amount)}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 hidden md:table-cell">
                          <TransactionStatusBadge status={tx.status} />
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Paginación */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-neutral-500">
                  Página {page + 1} de {totalPages}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={page === 0 || txLoading}
                    onClick={() => loadTransactions(page - 1)}
                  >
                    Anterior
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={page >= totalPages - 1 || txLoading}
                    onClick={() => loadTransactions(page + 1)}
                  >
                    Siguiente
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Modal de retiro */}
      <Modal
        isOpen={withdrawOpen}
        onClose={() => !withdrawLoading && setWithdrawOpen(false)}
        title={withdrawStep === 1 ? 'Solicitar retiro' : 'Confirma tu solicitud de retiro'}
      >
        {withdrawError && (
          <ErrorAlert message={withdrawError} className="mb-4" />
        )}

        {withdrawStep === 1 ? (
          <div className="space-y-5">
            {wallet && (
              <p className="text-sm text-neutral-400">
                Saldo disponible:{' '}
                <span className="font-semibold text-success-400">{formatCC(wallet.available_balance)}</span>
              </p>
            )}

            <div>
              <p className="text-sm font-medium text-neutral-300 mb-2">Método de retiro</p>
              <div className="space-y-2">
                {(['transferencia', 'paypal', 'cripto'] as WithdrawMethod[]).map((m) => (
                  <label
                    key={m}
                    className="flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors hover:bg-neutral-800 has-[:checked]:border-brand-500/50 has-[:checked]:bg-brand-500/5 border-neutral-700"
                  >
                    <input
                      type="radio"
                      name="method"
                      value={m}
                      checked={withdrawMethod === m}
                      onChange={() => setWithdrawMethod(m)}
                      className="accent-brand-500"
                    />
                    <span className="text-sm text-neutral-300">{methodLabels[m]}</span>
                  </label>
                ))}
              </div>
            </div>

            <Input
              label={withdrawMethod === 'paypal' ? 'Email de PayPal' : withdrawMethod === 'transferencia' ? 'IBAN / cuenta bancaria' : 'Dirección de wallet'}
              id="withdraw-dest"
              type="text"
              placeholder={destPlaceholders[withdrawMethod]}
              value={withdrawDest}
              onChange={(e) => {
                setWithdrawDest(e.target.value)
                setDestError(null)
              }}
              error={destError ?? undefined}
            />

            <Input
              label="Monto a retirar (CC)"
              id="withdraw-amount"
              type="number"
              min="10"
              step="0.01"
              placeholder="10,00"
              value={withdrawAmount}
              onChange={(e) => {
                setWithdrawAmount(e.target.value)
                setAmountError(null)
              }}
              error={amountError ?? undefined}
              helperText={!amountError ? `Mínimo: 10,00 CC · Máximo: ${wallet ? formatCC(wallet.available_balance) : '—'}` : undefined}
              suffix="CC"
            />

            <div className="border-t border-neutral-700 pt-4 flex justify-end gap-3">
              <Button variant="secondary" onClick={() => setWithdrawOpen(false)}>
                Cancelar
              </Button>
              <Button variant="primary" onClick={handleWithdrawNext}>
                Continuar
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            <div className="bg-neutral-800 rounded-lg p-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-neutral-500">Monto:</span>
                <span className="text-neutral-100 font-semibold tabular-nums">
                  {formatCC(parseFloat(withdrawAmount.replace(',', '.')))}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-neutral-500">Método:</span>
                <span className="text-neutral-300">{methodLabels[withdrawMethod]}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-neutral-500">Destino:</span>
                <span className="text-neutral-300 font-mono truncate max-w-[180px]">{withdrawDest}</span>
              </div>
            </div>

            <p className="text-sm text-neutral-400">
              Te contactaremos cuando se procese el retiro.
            </p>

            <div className="border-t border-neutral-700 pt-4 flex justify-end gap-3">
              <Button
                variant="secondary"
                disabled={withdrawLoading}
                onClick={() => setWithdrawStep(1)}
              >
                ← Volver
              </Button>
              <Button
                variant="primary"
                loading={withdrawLoading}
                onClick={handleWithdrawConfirm}
              >
                {withdrawLoading ? 'Procesando...' : 'Confirmar'}
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Modal de añadir créditos (placeholder, sin funcionalidad real todavía) */}
      <Modal
        isOpen={addCreditsOpen}
        onClose={() => setAddCreditsOpen(false)}
        title="Añadir créditos"
        size="sm"
      >
        <div className="space-y-5">
          <p className="text-sm text-neutral-400">
            Muy pronto podrás comprar créditos (CC) con tarjeta o PayPal. Esta función
            está en construcción.
          </p>

          <div className="border-t border-neutral-700 pt-4 flex justify-end">
            <Button variant="primary" onClick={() => setAddCreditsOpen(false)}>
              Entendido
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
