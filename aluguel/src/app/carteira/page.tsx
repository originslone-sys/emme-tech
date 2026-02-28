'use client'

import { useEffect, useState } from 'react'
import Header from '@/components/layout/Header'
import Modal from '@/components/ui/Modal'
import StatusBadge from '@/components/ui/StatusBadge'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { formatCurrency, formatDate } from '@/lib/utils'
import {
  Wallet,
  ArrowUpCircle,
  ArrowDownCircle,
  Receipt,
  DollarSign,
  TrendingUp,
  Clock,
  Send,
} from 'lucide-react'

interface WalletData {
  wallet: {
    balance: number
    totalReceived: number
    totalWithdrawn: number
    totalFees: number
  }
  withdrawals: {
    id: string
    amount: number
    status: string
    pixKey?: string
    bankName?: string
    createdAt: string
    processedAt?: string
  }[]
  recentCharges: {
    id: string
    value: number
    netValue: number
    platformFee: number
    paymentDate: string
    contract?: {
      property?: { name: string }
      tenant?: { name: string }
    }
  }[]
}

export default function CarteiraPage() {
  const [data, setData] = useState<WalletData | null>(null)
  const [loading, setLoading] = useState(true)
  const [withdrawModalOpen, setWithdrawModalOpen] = useState(false)
  const [form, setForm] = useState({ amount: '', pixKey: '', bankName: '', bankAgency: '', bankAccount: '' })
  const [paymentMethod, setPaymentMethod] = useState<'pix' | 'bank'>('pix')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const fetchData = async () => {
    try {
      const res = await fetch('/api/wallet')
      setData(await res.json())
    } catch (err) { console.error(err) }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchData() }, [])

  const handleWithdraw = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSaving(true)

    try {
      const res = await fetch('/api/wallet/withdraw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: parseFloat(form.amount),
          ...(paymentMethod === 'pix'
            ? { pixKey: form.pixKey }
            : { bankName: form.bankName, bankAgency: form.bankAgency, bankAccount: form.bankAccount }),
        }),
      })

      const result = await res.json()

      if (!res.ok) {
        setError(result.error)
        setSaving(false)
        return
      }

      setWithdrawModalOpen(false)
      setForm({ amount: '', pixKey: '', bankName: '', bankAgency: '', bankAccount: '' })
      fetchData()
    } catch {
      setError('Erro ao solicitar saque')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <LoadingSpinner size="lg" />

  const wallet = data?.wallet || { balance: 0, totalReceived: 0, totalWithdrawn: 0, totalFees: 0 }

  return (
    <div className="animate-fadeIn">
      <Header title="Carteira" />
      <div className="p-4 lg:p-8 space-y-6">
        {/* Balance Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="card bg-gradient-to-br from-primary-500 to-primary-700 text-white border-none">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-primary-100 text-sm font-medium">Saldo Disponível</p>
                <p className="text-3xl font-bold mt-1">{formatCurrency(wallet.balance)}</p>
              </div>
              <Wallet size={32} className="text-primary-200" />
            </div>
            <button
              onClick={() => setWithdrawModalOpen(true)}
              className="mt-4 w-full bg-white/20 hover:bg-white/30 text-white py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
              disabled={wallet.balance <= 0}
            >
              <Send size={16} /> Solicitar Saque
            </button>
          </div>

          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm font-medium">Total Recebido</p>
                <p className="text-2xl font-bold text-green-600 mt-1">{formatCurrency(wallet.totalReceived)}</p>
              </div>
              <div className="w-10 h-10 bg-green-50 rounded-xl flex items-center justify-center">
                <ArrowDownCircle size={20} className="text-green-600" />
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm font-medium">Total Sacado</p>
                <p className="text-2xl font-bold text-blue-600 mt-1">{formatCurrency(wallet.totalWithdrawn)}</p>
              </div>
              <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center">
                <ArrowUpCircle size={20} className="text-blue-600" />
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm font-medium">Taxas Pagas</p>
                <p className="text-2xl font-bold text-amber-600 mt-1">{formatCurrency(wallet.totalFees)}</p>
              </div>
              <div className="w-10 h-10 bg-amber-50 rounded-xl flex items-center justify-center">
                <Receipt size={20} className="text-amber-600" />
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Payments */}
          <div className="card p-0 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
              <TrendingUp size={18} className="text-green-600" />
              <h3 className="text-lg font-semibold text-gray-900">Últimos Recebimentos</h3>
            </div>
            <div className="divide-y divide-gray-100">
              {(data?.recentCharges || []).length === 0 ? (
                <div className="py-8 text-center text-gray-400 text-sm">Nenhum recebimento ainda</div>
              ) : (
                data?.recentCharges.map((ch) => (
                  <div key={ch.id} className="px-6 py-3 flex items-center justify-between hover:bg-gray-50/50">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{ch.contract?.property?.name}</p>
                      <p className="text-xs text-gray-500">{ch.contract?.tenant?.name} - {formatDate(ch.paymentDate)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-green-600">+{formatCurrency(ch.netValue)}</p>
                      <p className="text-xs text-gray-400">Taxa: {formatCurrency(ch.platformFee)}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Withdrawal History */}
          <div className="card p-0 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
              <Clock size={18} className="text-blue-600" />
              <h3 className="text-lg font-semibold text-gray-900">Histórico de Saques</h3>
            </div>
            <div className="divide-y divide-gray-100">
              {(data?.withdrawals || []).length === 0 ? (
                <div className="py-8 text-center text-gray-400 text-sm">Nenhum saque solicitado</div>
              ) : (
                data?.withdrawals.map((w) => (
                  <div key={w.id} className="px-6 py-3 flex items-center justify-between hover:bg-gray-50/50">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{formatCurrency(w.amount)}</p>
                      <p className="text-xs text-gray-500">
                        {w.pixKey ? `PIX: ${w.pixKey}` : w.bankName} - {formatDate(w.createdAt)}
                      </p>
                    </div>
                    <StatusBadge status={w.status} />
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Withdraw Modal */}
      <Modal isOpen={withdrawModalOpen} onClose={() => setWithdrawModalOpen(false)} title="Solicitar Saque" size="md">
        <form onSubmit={handleWithdraw} className="space-y-4">
          {error && (
            <div className="bg-red-50 text-red-700 text-sm rounded-lg px-4 py-3 border border-red-100">{error}</div>
          )}

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
            <p className="text-sm text-blue-600 font-medium">Saldo Disponível</p>
            <p className="text-2xl font-bold text-blue-700">{formatCurrency(wallet.balance)}</p>
          </div>

          <div>
            <label className="label-field">Valor do Saque (R$) *</label>
            <input
              type="number" step="0.01" min="1" max={wallet.balance}
              value={form.amount}
              onChange={(e) => setForm({ ...form, amount: e.target.value })}
              className="input-field" placeholder="0,00" required
            />
          </div>

          <div>
            <label className="label-field">Método de Recebimento</label>
            <div className="grid grid-cols-2 gap-3">
              <button type="button" onClick={() => setPaymentMethod('pix')}
                className={`p-3 rounded-lg border text-sm font-medium transition-colors ${paymentMethod === 'pix' ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-gray-200 hover:bg-gray-50'}`}>
                PIX
              </button>
              <button type="button" onClick={() => setPaymentMethod('bank')}
                className={`p-3 rounded-lg border text-sm font-medium transition-colors ${paymentMethod === 'bank' ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-gray-200 hover:bg-gray-50'}`}>
                Transferência Bancária
              </button>
            </div>
          </div>

          {paymentMethod === 'pix' ? (
            <div>
              <label className="label-field">Chave PIX *</label>
              <input value={form.pixKey} onChange={(e) => setForm({ ...form, pixKey: e.target.value })}
                className="input-field" placeholder="CPF, E-mail, Telefone ou Chave Aleatória" required />
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="label-field">Banco *</label>
                <input value={form.bankName} onChange={(e) => setForm({ ...form, bankName: e.target.value })}
                  className="input-field" placeholder="Nome do banco" required />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label-field">Agência *</label>
                  <input value={form.bankAgency} onChange={(e) => setForm({ ...form, bankAgency: e.target.value })}
                    className="input-field" placeholder="0000" required />
                </div>
                <div>
                  <label className="label-field">Conta *</label>
                  <input value={form.bankAccount} onChange={(e) => setForm({ ...form, bankAccount: e.target.value })}
                    className="input-field" placeholder="00000-0" required />
                </div>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
            <button type="button" onClick={() => setWithdrawModalOpen(false)} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-success" disabled={saving}>
              {saving ? 'Processando...' : 'Solicitar Saque'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
