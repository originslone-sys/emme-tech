'use client'

import { useEffect, useState } from 'react'
import Header from '@/components/layout/Header'
import DataTable from '@/components/ui/DataTable'
import Modal from '@/components/ui/Modal'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { formatCurrency, formatPhone, formatCpfCnpj } from '@/lib/utils'
import { Plus, Edit, Trash2 } from 'lucide-react'

interface Tenant {
  id: string
  name: string
  email: string
  phone: string
  cpfCnpj: string
  birthDate?: string
  address?: string
  profession?: string
  monthlyIncome?: number
  notes?: string
  contracts?: { id: string; property: { name: string } }[]
}

const emptyForm = {
  name: '', email: '', phone: '', cpfCnpj: '', birthDate: '',
  address: '', profession: '', monthlyIncome: '', notes: '',
}

export default function InquilinosPage() {
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [deleteDialog, setDeleteDialog] = useState<string | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const fetchTenants = async () => {
    try {
      const res = await fetch('/api/inquilinos')
      setTenants(await res.json())
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchTenants() }, [])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const openCreate = () => { setForm(emptyForm); setEditingId(null); setModalOpen(true) }

  const openEdit = (t: Tenant) => {
    setForm({
      name: t.name, email: t.email, phone: t.phone, cpfCnpj: t.cpfCnpj,
      birthDate: t.birthDate ? t.birthDate.split('T')[0] : '',
      address: t.address || '', profession: t.profession || '',
      monthlyIncome: t.monthlyIncome ? String(t.monthlyIncome) : '', notes: t.notes || '',
    })
    setEditingId(t.id)
    setModalOpen(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const url = editingId ? `/api/inquilinos/${editingId}` : '/api/inquilinos'
      const res = await fetch(url, {
        method: editingId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (res.ok) { setModalOpen(false); fetchTenants() }
    } catch (err) { console.error(err) }
    finally { setSaving(false) }
  }

  const handleDelete = async (id: string) => {
    try {
      await fetch(`/api/inquilinos/${id}`, { method: 'DELETE' })
      setDeleteDialog(null)
      fetchTenants()
    } catch (err) { console.error(err) }
  }

  if (loading) return <LoadingSpinner size="lg" />

  const columns = [
    { key: 'name', label: 'Nome', render: (t: Tenant) => <span className="font-medium text-gray-900">{t.name}</span> },
    { key: 'email', label: 'E-mail' },
    { key: 'phone', label: 'Telefone', render: (t: Tenant) => formatPhone(t.phone) },
    { key: 'cpfCnpj', label: 'CPF/CNPJ', render: (t: Tenant) => formatCpfCnpj(t.cpfCnpj) },
    {
      key: 'contracts', label: 'Imóvel',
      render: (t: Tenant) => t.contracts && t.contracts.length > 0
        ? <span className="badge bg-blue-100 text-blue-800">{t.contracts[0].property.name}</span>
        : <span className="text-gray-400 text-xs">Sem contrato</span>
    },
  ]

  return (
    <div className="animate-fadeIn">
      <Header title="Inquilinos" />
      <div className="p-4 lg:p-8">
        <div className="page-header">
          <div>
            <h1 className="page-title">Inquilinos</h1>
            <p className="text-gray-500 text-sm mt-1">{tenants.length} inquilino(s) cadastrado(s)</p>
          </div>
          <button onClick={openCreate} className="btn-primary"><Plus size={18} /> Novo Inquilino</button>
        </div>

        <DataTable columns={columns} data={tenants} searchPlaceholder="Buscar inquilino..."
          actions={(t) => (
            <div className="flex items-center gap-1">
              <button onClick={() => openEdit(t)} className="p-2 text-gray-500 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"><Edit size={16} /></button>
              <button onClick={() => setDeleteDialog(t.id)} className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"><Trash2 size={16} /></button>
            </div>
          )}
        />
      </div>

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editingId ? 'Editar Inquilino' : 'Novo Inquilino'} size="lg">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label-field">Nome Completo *</label>
              <input name="name" value={form.name} onChange={handleChange} className="input-field" required />
            </div>
            <div>
              <label className="label-field">E-mail *</label>
              <input name="email" type="email" value={form.email} onChange={handleChange} className="input-field" required />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="label-field">Telefone *</label>
              <input name="phone" value={form.phone} onChange={handleChange} className="input-field" placeholder="(11) 99999-9999" required />
            </div>
            <div>
              <label className="label-field">CPF/CNPJ *</label>
              <input name="cpfCnpj" value={form.cpfCnpj} onChange={handleChange} className="input-field" required />
            </div>
            <div>
              <label className="label-field">Data de Nascimento</label>
              <input name="birthDate" type="date" value={form.birthDate} onChange={handleChange} className="input-field" />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label-field">Profissão</label>
              <input name="profession" value={form.profession} onChange={handleChange} className="input-field" />
            </div>
            <div>
              <label className="label-field">Renda Mensal (R$)</label>
              <input name="monthlyIncome" type="number" step="0.01" value={form.monthlyIncome} onChange={handleChange} className="input-field" />
            </div>
          </div>
          <div>
            <label className="label-field">Endereço</label>
            <input name="address" value={form.address} onChange={handleChange} className="input-field" />
          </div>
          <div>
            <label className="label-field">Observações</label>
            <textarea name="notes" value={form.notes} onChange={handleChange} rows={3} className="input-field" />
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Salvando...' : editingId ? 'Atualizar' : 'Cadastrar'}</button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog isOpen={!!deleteDialog} onClose={() => setDeleteDialog(null)}
        onConfirm={() => deleteDialog && handleDelete(deleteDialog)}
        title="Excluir Inquilino" message="Tem certeza que deseja excluir este inquilino?" confirmLabel="Excluir" />
    </div>
  )
}
