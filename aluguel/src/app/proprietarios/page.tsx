'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import Header from '@/components/layout/Header'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { formatCurrency, formatPhone, formatCpfCnpj } from '@/lib/utils'
import { Building2, FileText, Receipt, User } from 'lucide-react'

export default function ProprietariosPage() {
  const { data: session } = useSession()
  const [stats, setStats] = useState({ properties: 0, contracts: 0, charges: 0 })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [props, contracts, charges] = await Promise.all([
          fetch('/api/imoveis').then(r => r.json()),
          fetch('/api/contratos').then(r => r.json()),
          fetch('/api/cobrancas').then(r => r.json()),
        ])
        setStats({
          properties: props.length,
          contracts: contracts.filter((c: any) => c.status === 'ACTIVE').length,
          charges: charges.filter((c: any) => c.status === 'CONFIRMED').length,
        })
      } catch (err) { console.error(err) }
      finally { setLoading(false) }
    }
    fetchStats()
  }, [])

  if (loading) return <LoadingSpinner size="lg" />

  const user = session?.user

  return (
    <div className="animate-fadeIn">
      <Header title="Proprietários" />
      <div className="p-4 lg:p-8">
        <div className="page-header">
          <div>
            <h1 className="page-title">Meu Perfil</h1>
            <p className="text-gray-500 text-sm mt-1">Informações do proprietário</p>
          </div>
        </div>

        {/* Profile Card */}
        <div className="card mb-6">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center">
              <User size={28} className="text-primary-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">{user?.name}</h2>
              <p className="text-gray-500">{user?.email}</p>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="card-hover flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center">
              <Building2 size={24} className="text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Imóveis Cadastrados</p>
              <p className="text-2xl font-bold text-gray-900">{stats.properties}</p>
            </div>
          </div>
          <div className="card-hover flex items-center gap-4">
            <div className="w-12 h-12 bg-green-50 rounded-xl flex items-center justify-center">
              <FileText size={24} className="text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Contratos Ativos</p>
              <p className="text-2xl font-bold text-gray-900">{stats.contracts}</p>
            </div>
          </div>
          <div className="card-hover flex items-center gap-4">
            <div className="w-12 h-12 bg-purple-50 rounded-xl flex items-center justify-center">
              <Receipt size={24} className="text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Cobranças Recebidas</p>
              <p className="text-2xl font-bold text-gray-900">{stats.charges}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
