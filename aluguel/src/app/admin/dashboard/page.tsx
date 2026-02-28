'use client'

import { useEffect, useState } from 'react'
import Header from '@/components/layout/Header'
import StatsCard from '@/components/ui/StatsCard'
import StatusBadge from '@/components/ui/StatusBadge'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { formatCurrency, formatDate } from '@/lib/utils'
import {
  Users,
  Building2,
  FileText,
  DollarSign,
  Receipt,
  ArrowUpCircle,
  CheckCircle,
  XCircle,
} from 'lucide-react'

interface AdminDashboard {
  totalUsers: number
  activeUsers: number
  totalProperties: number
  totalContracts: number
  platformRevenue: number
  totalCharges: number
  pendingWithdrawals: any[]
  recentUsers: any[]
  recentWithdrawals: any[]
}

export default function AdminDashboardPage() {
  const [data, setData] = useState<AdminDashboard | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    try {
      const res = await fetch('/api/admin/dashboard')
      if (res.ok) setData(await res.json())
    } catch (err) { console.error(err) }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchData() }, [])

  const handleWithdrawal = async (id: string, status: string) => {
    try {
      await fetch(`/api/admin/withdrawals/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      })
      fetchData()
    } catch (err) { console.error(err) }
  }

  if (loading) return <LoadingSpinner size="lg" />

  return (
    <div className="animate-fadeIn">
      <Header title="Painel Administrativo" />
      <div className="p-4 lg:p-8 space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCard title="Total Usuários" value={String(data?.totalUsers || 0)} icon={Users} color="blue" />
          <StatsCard title="Imóveis Cadastrados" value={String(data?.totalProperties || 0)} icon={Building2} color="green" />
          <StatsCard title="Contratos Ativos" value={String(data?.totalContracts || 0)} icon={FileText} color="purple" />
          <StatsCard title="Receita Plataforma (Mês)" value={formatCurrency(data?.platformRevenue || 0)} icon={DollarSign} color="green" />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="card bg-gradient-to-br from-green-500 to-green-700 text-white border-none">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-green-100 text-sm font-medium">Cobranças Recebidas (Mês)</p>
                <p className="text-3xl font-bold mt-1">{data?.totalCharges || 0}</p>
              </div>
              <Receipt size={32} className="text-green-200" />
            </div>
            <p className="text-green-100 text-sm mt-2">
              = {formatCurrency((data?.totalCharges || 0) * 20)} em taxas
            </p>
          </div>
          <div className="card bg-gradient-to-br from-amber-500 to-amber-700 text-white border-none">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-amber-100 text-sm font-medium">Saques Pendentes</p>
                <p className="text-3xl font-bold mt-1">{data?.pendingWithdrawals?.length || 0}</p>
              </div>
              <ArrowUpCircle size={32} className="text-amber-200" />
            </div>
            <p className="text-amber-100 text-sm mt-2">
              Total: {formatCurrency(data?.pendingWithdrawals?.reduce((s: number, w: any) => s + w.amount, 0) || 0)}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Pending Withdrawals */}
          <div className="card p-0 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="text-lg font-semibold text-gray-900">Saques Pendentes</h3>
            </div>
            <div className="divide-y divide-gray-100">
              {(data?.pendingWithdrawals || []).length === 0 ? (
                <div className="py-8 text-center text-gray-400 text-sm">Nenhum saque pendente</div>
              ) : (
                data?.pendingWithdrawals.map((w: any) => (
                  <div key={w.id} className="px-6 py-3 flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{w.user?.name}</p>
                      <p className="text-xs text-gray-500">{w.user?.email}</p>
                      <p className="text-sm font-semibold text-gray-900 mt-1">{formatCurrency(w.amount)}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleWithdrawal(w.id, 'COMPLETED')}
                        className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                        title="Aprovar"
                      >
                        <CheckCircle size={20} />
                      </button>
                      <button
                        onClick={() => handleWithdrawal(w.id, 'REJECTED')}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Rejeitar"
                      >
                        <XCircle size={20} />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Recent Users */}
          <div className="card p-0 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="text-lg font-semibold text-gray-900">Usuários Recentes</h3>
            </div>
            <div className="divide-y divide-gray-100">
              {(data?.recentUsers || []).map((u: any) => (
                <div key={u.id} className="px-6 py-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{u.name}</p>
                    <p className="text-xs text-gray-500">{u.email}</p>
                  </div>
                  <div className="text-right">
                    <StatusBadge status={u.role === 'ADMIN' ? 'CONFIRMED' : 'PENDING'} />
                    <p className="text-xs text-gray-400 mt-1">{formatDate(u.createdAt)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
