'use client'

import { useEffect, useState } from 'react'
import Header from '@/components/layout/Header'
import DataTable from '@/components/ui/DataTable'
import Modal from '@/components/ui/Modal'
import StatusBadge from '@/components/ui/StatusBadge'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { formatCurrency, formatDate } from '@/lib/utils'
import { Edit, Shield, ShieldOff, Eye } from 'lucide-react'

interface AdminUser {
  id: string
  name: string
  email: string
  phone?: string
  cpfCnpj?: string
  role: string
  isActive: boolean
  createdAt: string
  _count: { properties: number; contracts: number; charges: number }
  wallet?: { balance: number; totalReceived: number; totalFees: number }
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [editModal, setEditModal] = useState<AdminUser | null>(null)
  const [saving, setSaving] = useState(false)

  const fetchUsers = async () => {
    try {
      const res = await fetch('/api/admin/users')
      if (res.ok) setUsers(await res.json())
    } catch (err) { console.error(err) }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchUsers() }, [])

  const handleToggleActive = async (user: AdminUser) => {
    try {
      await fetch(`/api/admin/users/${user.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isActive: !user.isActive }),
      })
      fetchUsers()
    } catch (err) { console.error(err) }
  }

  const handleToggleRole = async (user: AdminUser) => {
    try {
      await fetch(`/api/admin/users/${user.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: user.role === 'ADMIN' ? 'CLIENT' : 'ADMIN' }),
      })
      fetchUsers()
    } catch (err) { console.error(err) }
  }

  if (loading) return <LoadingSpinner size="lg" />

  const columns = [
    { key: 'name', label: 'Nome', render: (u: AdminUser) => (
      <div>
        <span className="font-medium text-gray-900">{u.name}</span>
        {u.role === 'ADMIN' && <span className="ml-2 badge bg-purple-100 text-purple-800">Admin</span>}
      </div>
    ) },
    { key: 'email', label: 'E-mail' },
    { key: 'properties', label: 'Imóveis', render: (u: AdminUser) => u._count.properties },
    { key: 'contracts', label: 'Contratos', render: (u: AdminUser) => u._count.contracts },
    { key: 'balance', label: 'Saldo', render: (u: AdminUser) => (
      <span className="font-semibold">{formatCurrency(u.wallet?.balance || 0)}</span>
    ) },
    { key: 'fees', label: 'Taxas Pagas', render: (u: AdminUser) => (
      <span className="text-green-600">{formatCurrency(u.wallet?.totalFees || 0)}</span>
    ) },
    { key: 'isActive', label: 'Status', render: (u: AdminUser) => (
      <StatusBadge status={u.isActive ? 'ACTIVE' : 'CANCELLED'} />
    ) },
    { key: 'createdAt', label: 'Criado em', render: (u: AdminUser) => formatDate(u.createdAt) },
  ]

  return (
    <div className="animate-fadeIn">
      <Header title="Gerenciar Usuários" />
      <div className="p-4 lg:p-8">
        <div className="page-header">
          <div>
            <h1 className="page-title">Usuários do Sistema</h1>
            <p className="text-gray-500 text-sm mt-1">{users.length} usuário(s) cadastrado(s)</p>
          </div>
        </div>

        {/* Summary */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="card">
            <p className="text-sm text-gray-500">Total</p>
            <p className="text-2xl font-bold text-gray-900">{users.length}</p>
          </div>
          <div className="card">
            <p className="text-sm text-gray-500">Ativos</p>
            <p className="text-2xl font-bold text-green-600">{users.filter(u => u.isActive).length}</p>
          </div>
          <div className="card">
            <p className="text-sm text-gray-500">Receita Total em Taxas</p>
            <p className="text-2xl font-bold text-primary-600">
              {formatCurrency(users.reduce((sum, u) => sum + (u.wallet?.totalFees || 0), 0))}
            </p>
          </div>
        </div>

        <DataTable columns={columns} data={users} searchPlaceholder="Buscar usuário..."
          actions={(u) => (
            <div className="flex items-center gap-1">
              <button onClick={() => handleToggleRole(u)}
                className="p-2 text-gray-500 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                title={u.role === 'ADMIN' ? 'Remover Admin' : 'Tornar Admin'}>
                {u.role === 'ADMIN' ? <ShieldOff size={16} /> : <Shield size={16} />}
              </button>
              <button onClick={() => handleToggleActive(u)}
                className={`p-2 rounded-lg transition-colors ${u.isActive
                  ? 'text-gray-500 hover:text-red-600 hover:bg-red-50'
                  : 'text-gray-500 hover:text-green-600 hover:bg-green-50'}`}
                title={u.isActive ? 'Desativar' : 'Ativar'}>
                <Edit size={16} />
              </button>
            </div>
          )}
        />
      </div>
    </div>
  )
}
