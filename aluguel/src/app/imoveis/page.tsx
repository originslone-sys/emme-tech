'use client'

import { useEffect, useState } from 'react'
import Header from '@/components/layout/Header'
import DataTable from '@/components/ui/DataTable'
import Modal from '@/components/ui/Modal'
import StatusBadge from '@/components/ui/StatusBadge'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { formatCurrency } from '@/lib/utils'
import { PROPERTY_TYPES, BRAZILIAN_STATES } from '@/lib/utils'
import { Plus, Edit, Trash2, Eye } from 'lucide-react'

interface Property {
  id: string
  name: string
  type: string
  address: string
  neighborhood: string
  city: string
  state: string
  zipCode: string
  rentValue: number
  condoFee: number
  iptuValue: number
  status: string
  number?: string
  complement?: string
  description?: string
  contracts?: { id: string }[]
}

const emptyForm = {
  name: '', type: 'Apartamento', address: '', number: '', complement: '',
  neighborhood: '', city: '', state: 'SP', zipCode: '',
  rentValue: '', condoFee: '', iptuValue: '', description: '',
}

export default function ImoveisPage() {
  const [properties, setProperties] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [deleteDialog, setDeleteDialog] = useState<string | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const fetchProperties = async () => {
    try {
      const res = await fetch('/api/imoveis')
      const data = await res.json()
      setProperties(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchProperties() }, [])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const openCreate = () => {
    setForm(emptyForm)
    setEditingId(null)
    setModalOpen(true)
  }

  const openEdit = (p: Property) => {
    setForm({
      name: p.name, type: p.type, address: p.address, number: p.number || '',
      complement: p.complement || '', neighborhood: p.neighborhood, city: p.city,
      state: p.state, zipCode: p.zipCode, rentValue: String(p.rentValue),
      condoFee: String(p.condoFee || ''), iptuValue: String(p.iptuValue || ''),
      description: p.description || '',
    })
    setEditingId(p.id)
    setModalOpen(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)

    try {
      const url = editingId ? `/api/imoveis/${editingId}` : '/api/imoveis'
      const method = editingId ? 'PUT' : 'POST'

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })

      if (res.ok) {
        setModalOpen(false)
        fetchProperties()
      }
    } catch (err) {
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await fetch(`/api/imoveis/${id}`, { method: 'DELETE' })
      setDeleteDialog(null)
      fetchProperties()
    } catch (err) {
      console.error(err)
    }
  }

  if (loading) return <LoadingSpinner size="lg" />

  const columns = [
    { key: 'name', label: 'Nome', render: (p: Property) => <span className="font-medium text-gray-900">{p.name}</span> },
    { key: 'type', label: 'Tipo' },
    { key: 'address', label: 'Endereço', render: (p: Property) => `${p.address}, ${p.neighborhood} - ${p.city}/${p.state}` },
    { key: 'rentValue', label: 'Aluguel', render: (p: Property) => <span className="font-semibold">{formatCurrency(p.rentValue)}</span> },
    { key: 'status', label: 'Status', render: (p: Property) => <StatusBadge status={p.status} /> },
  ]

  return (
    <div className="animate-fadeIn">
      <Header title="Imóveis" />

      <div className="p-4 lg:p-8">
        <div className="page-header">
          <div>
            <h1 className="page-title">Meus Imóveis</h1>
            <p className="text-gray-500 text-sm mt-1">{properties.length} imóvel(is) cadastrado(s)</p>
          </div>
          <button onClick={openCreate} className="btn-primary">
            <Plus size={18} /> Novo Imóvel
          </button>
        </div>

        <DataTable
          columns={columns}
          data={properties}
          searchPlaceholder="Buscar imóvel..."
          actions={(p) => (
            <div className="flex items-center gap-1">
              <button onClick={() => openEdit(p)} className="p-2 text-gray-500 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors">
                <Edit size={16} />
              </button>
              <button onClick={() => setDeleteDialog(p.id)} className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
                <Trash2 size={16} />
              </button>
            </div>
          )}
        />
      </div>

      {/* Create/Edit Modal */}
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editingId ? 'Editar Imóvel' : 'Novo Imóvel'} size="lg">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label-field">Nome do Imóvel *</label>
              <input name="name" value={form.name} onChange={handleChange} className="input-field" placeholder="Ex: Apt 302 - Ed. Solar" required />
            </div>
            <div>
              <label className="label-field">Tipo *</label>
              <select name="type" value={form.type} onChange={handleChange} className="input-field">
                {PROPERTY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <label className="label-field">Endereço *</label>
              <input name="address" value={form.address} onChange={handleChange} className="input-field" placeholder="Rua / Avenida" required />
            </div>
            <div>
              <label className="label-field">Número</label>
              <input name="number" value={form.number} onChange={handleChange} className="input-field" placeholder="123" />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="label-field">Complemento</label>
              <input name="complement" value={form.complement} onChange={handleChange} className="input-field" placeholder="Bloco A" />
            </div>
            <div>
              <label className="label-field">Bairro *</label>
              <input name="neighborhood" value={form.neighborhood} onChange={handleChange} className="input-field" required />
            </div>
            <div>
              <label className="label-field">CEP *</label>
              <input name="zipCode" value={form.zipCode} onChange={handleChange} className="input-field" placeholder="00000-000" required />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label-field">Cidade *</label>
              <input name="city" value={form.city} onChange={handleChange} className="input-field" required />
            </div>
            <div>
              <label className="label-field">Estado *</label>
              <select name="state" value={form.state} onChange={handleChange} className="input-field">
                {BRAZILIAN_STATES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="label-field">Valor Aluguel (R$) *</label>
              <input name="rentValue" type="number" step="0.01" value={form.rentValue} onChange={handleChange} className="input-field" placeholder="1500.00" required />
            </div>
            <div>
              <label className="label-field">Condomínio (R$)</label>
              <input name="condoFee" type="number" step="0.01" value={form.condoFee} onChange={handleChange} className="input-field" placeholder="300.00" />
            </div>
            <div>
              <label className="label-field">IPTU (R$)</label>
              <input name="iptuValue" type="number" step="0.01" value={form.iptuValue} onChange={handleChange} className="input-field" placeholder="150.00" />
            </div>
          </div>

          <div>
            <label className="label-field">Descrição</label>
            <textarea name="description" value={form.description} onChange={handleChange} rows={3} className="input-field" placeholder="Observações sobre o imóvel..." />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Salvando...' : editingId ? 'Atualizar' : 'Cadastrar'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirm */}
      <ConfirmDialog
        isOpen={!!deleteDialog}
        onClose={() => setDeleteDialog(null)}
        onConfirm={() => deleteDialog && handleDelete(deleteDialog)}
        title="Excluir Imóvel"
        message="Tem certeza que deseja excluir este imóvel? Esta ação não pode ser desfeita."
        confirmLabel="Excluir"
      />
    </div>
  )
}
