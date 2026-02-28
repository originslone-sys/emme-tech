'use client'

import { useEffect, useState } from 'react'
import Header from '@/components/layout/Header'
import StatsCard from '@/components/ui/StatsCard'
import StatusBadge from '@/components/ui/StatusBadge'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { formatCurrency, formatDate } from '@/lib/utils'
import {
  DollarSign,
  Clock,
  AlertTriangle,
  Building2,
  TrendingUp,
  FileText,
  Receipt,
  Calendar,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'

interface DashboardData {
  stats: {
    totalReceived: number
    totalPending: number
    totalOverdue: number
    occupancyRate: number
    receiptRate: number
    activeContracts: number
    averageTicket: number
    next7Days: number
  }
  monthlyCharges: any[]
  last6MonthsRevenue: { month: string; value: number }[]
  monthStatus: { confirmed: number; pending: number; overdue: number; cancelled: number }
}

const PIE_COLORS = ['#22c55e', '#f59e0b', '#ef4444', '#94a3b8']

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/dashboard')
      .then(res => res.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner size="lg" />

  const stats = data?.stats || {
    totalReceived: 0, totalPending: 0, totalOverdue: 0, occupancyRate: 0,
    receiptRate: 0, activeContracts: 0, averageTicket: 0, next7Days: 0,
  }

  const pieData = data ? [
    { name: 'Confirmadas', value: data.monthStatus.confirmed },
    { name: 'Pendentes', value: data.monthStatus.pending },
    { name: 'Atrasadas', value: data.monthStatus.overdue },
    { name: 'Canceladas', value: data.monthStatus.cancelled },
  ].filter(d => d.value > 0) : []

  return (
    <div className="animate-fadeIn">
      <Header title="Dashboard" />

      <div className="p-4 lg:p-8 space-y-6">
        {/* Stats Cards Row 1 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCard
            title="RECEBIDO"
            value={formatCurrency(stats.totalReceived)}
            icon={DollarSign}
            color="green"
          />
          <StatsCard
            title="EM ABERTO"
            value={formatCurrency(stats.totalPending)}
            icon={Clock}
            color="yellow"
          />
          <StatsCard
            title="ATRASADAS"
            value={String(stats.totalOverdue)}
            icon={AlertTriangle}
            color="red"
          />
          <StatsCard
            title="OCUPAÇÃO"
            value={`${stats.occupancyRate}%`}
            icon={Building2}
            color="blue"
          />
        </div>

        {/* Stats Cards Row 2 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCard
            title="Taxa Recebimento"
            value={`${stats.receiptRate}%`}
            icon={TrendingUp}
            color="green"
          />
          <StatsCard
            title="Contratos Ativos"
            value={String(stats.activeContracts)}
            icon={FileText}
            color="blue"
          />
          <StatsCard
            title="Ticket Médio"
            value={formatCurrency(stats.averageTicket)}
            icon={Receipt}
            color="purple"
          />
          <StatsCard
            title="Próx. 7 dias"
            value={String(stats.next7Days)}
            icon={Calendar}
            color="yellow"
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Revenue Chart */}
          <div className="card lg:col-span-2">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Receita últimos 6 meses</h3>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data?.last6MonthsRevenue || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#64748b' }} />
                  <YAxis tick={{ fontSize: 12, fill: '#64748b' }} tickFormatter={(v) => `R$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip
                    formatter={(value: number) => [formatCurrency(value), 'Receita']}
                    contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0' }}
                  />
                  <Bar dataKey="value" fill="#3b82f6" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Monthly Status Pie */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Status do Mês</h3>
            {pieData.length > 0 ? (
              <div className="h-72 flex flex-col items-center">
                <ResponsiveContainer width="100%" height="80%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={4}
                      dataKey="value"
                    >
                      {pieData.map((_, idx) => (
                        <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex flex-wrap gap-3 justify-center">
                  {pieData.map((d, idx) => (
                    <div key={d.name} className="flex items-center gap-1.5 text-xs text-gray-600">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: PIE_COLORS[idx] }} />
                      {d.name} ({d.value})
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="h-72 flex items-center justify-center text-gray-400 text-sm">
                Sem dados para o mês atual
              </div>
            )}
          </div>
        </div>

        {/* Monthly Charges Table */}
        <div className="card p-0 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900">Cobranças do Mês</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50/80">
                  <th className="table-header">Imóvel</th>
                  <th className="table-header">Inquilino</th>
                  <th className="table-header">Valor</th>
                  <th className="table-header">Vencimento</th>
                  <th className="table-header">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(data?.monthlyCharges || []).length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-gray-400 text-sm">
                      Nenhuma cobrança para este mês
                    </td>
                  </tr>
                ) : (
                  data?.monthlyCharges.map((charge: any) => (
                    <tr key={charge.id} className="hover:bg-gray-50/50">
                      <td className="table-cell font-medium">{charge.contract?.property?.name}</td>
                      <td className="table-cell">{charge.contract?.tenant?.name}</td>
                      <td className="table-cell font-semibold">{formatCurrency(charge.value)}</td>
                      <td className="table-cell">{formatDate(charge.dueDate)}</td>
                      <td className="table-cell"><StatusBadge status={charge.status} /></td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
