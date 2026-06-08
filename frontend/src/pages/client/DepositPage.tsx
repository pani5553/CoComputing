import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BanknotesIcon, CheckCircleIcon } from '@heroicons/react/24/outline'
import { deposit } from '../../api/clientApi'
import { extractErrorMessage } from '../../api/client'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import ErrorAlert from '../../components/ui/ErrorAlert'
import { formatCC } from '../../utils/format'

const PRESETS = [50, 100, 250, 500]

export default function DepositPage() {
  const navigate = useNavigate()
  const [amount, setAmount] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<{ amount: number; newBalance: number } | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const parsed = parseFloat(amount)
    if (!parsed || parsed <= 0) {
      setError('Introduce un importe válido mayor que 0.')
      return
    }
    setError(null)
    setLoading(true)
    try {
      const result = await deposit({ amount: parsed })
      setSuccess({ amount: result.amount, newBalance: result.new_available_balance })
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="max-w-md mx-auto mt-12 px-4 text-center">
        <CheckCircleIcon className="h-16 w-16 text-brand-400 mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-neutral-100 mb-2">¡Depósito realizado!</h1>
        <p className="text-neutral-400 mb-1">
          Has añadido <span className="text-brand-400 font-semibold">{formatCC(success.amount)}</span> a tu cartera.
        </p>
        <p className="text-neutral-500 text-sm mb-8">
          Saldo disponible: <span className="text-neutral-300">{formatCC(success.newBalance)}</span>
        </p>
        <div className="flex gap-3 justify-center">
          <Button variant="secondary" onClick={() => { setSuccess(null); setAmount('') }}>
            Otro depósito
          </Button>
          <Button onClick={() => navigate('/cliente/publicar')}>
            Publicar tarea
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-md mx-auto mt-8 px-4">
      <div className="flex items-center gap-3 mb-6">
        <BanknotesIcon className="h-8 w-8 text-brand-400" />
        <div>
          <h1 className="text-2xl font-bold text-neutral-100">Recargar saldo</h1>
          <p className="text-sm text-neutral-400">Depósito simulado de Co-Computing Credits (CC)</p>
        </div>
      </div>

      <div className="bg-neutral-900 border border-neutral-700 rounded-xl p-6">
        <p className="text-sm text-neutral-400 mb-4">
          Selecciona un importe o introduce el que quieras:
        </p>

        <div className="grid grid-cols-4 gap-2 mb-5">
          {PRESETS.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setAmount(String(p))}
              className={`py-2 rounded-lg text-sm font-semibold border transition-all ${
                amount === String(p)
                  ? 'bg-brand-500/20 border-brand-500 text-brand-400'
                  : 'border-neutral-700 text-neutral-400 hover:border-neutral-500 hover:text-neutral-200'
              }`}
            >
              {p} CC
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Importe (CC)"
            type="number"
            min="1"
            step="0.01"
            placeholder="Ej: 100"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
          />
          {error && <ErrorAlert message={error} />}
          <Button type="submit" loading={loading} className="w-full">
            Depositar{amount && parseFloat(amount) > 0 ? ` ${formatCC(parseFloat(amount))}` : ''}
          </Button>
        </form>
      </div>

      <p className="text-xs text-neutral-600 mt-4 text-center">
        Los CC son moneda virtual de la plataforma. El depósito es simulado.
      </p>
    </div>
  )
}
