'use client'

import { useEffect, useState } from 'react'
import Header from '@/components/layout/Header'
import DataTable from '@/components/ui/DataTable'
import Modal from '@/components/ui/Modal'
import StatusBadge from '@/components/ui/StatusBadge'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { formatCurrency, formatDate } from '@/lib/utils'
import { Plus, Edit, Trash2, XCircle } from 'lucide-react'

interface Contract {
  id: string
  propertyId: string
  tenantId: string
  startDate: string
  endDate: string
  rentValue: number
  dueDay: number
  deposit: number
  adjustmentIndex: string
  status: string
  notes?: string
  property?: { name: string; address: string; city: string }
  tenant?: { name: string; email: string; phone: string }
}

interface Property { id: string; name: string; rentValue: number; status: string }
interface Tenant { id: string; name: string }

const emptyForm = {
  propertyId: '', tenantId: '', startDate: '', endDate: '',
  rentValue: '', dueDay: '10', deposit: '', adjustmentIndex: 'IGPM', notes: '',
}

export default function ContratosPage() {
  const [contracts, setContracts] = useState<Contract[]>([])
  const [properties, setProperties] = useState<Property[]>([])
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [deleteDialog, setDeleteDialog] = useState<string | null>(null)
  const [cancelDialog, setCancelDialog] = useState<string | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const fetchAll = async () => {
    try {
      const [c, p, t] = await Promise.all([
        fetch('/api/contratos').then(r => r.json()),
        fetch('/api/imoveis').then(r => r.json()),
        fetch('/api/inquilinos').then(r => r.json()),
      ])
      setContracts(c)
      setProperties(p)
      setTenants(t)
    } catch (err) { console.error(err) }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchAll() }, [])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const newForm = { ...form, [e.target.name]: e.target.value }
    // Auto-fill rent value when property is selected
    if (e.target.name === 'propertyId') {
      const prop = properties.find(p => p.id === e.target.value)
      if (prop) newForm.rentValue = String(prop.rentValue)
    }
    setForm(newForm)
  }

  const openCreate = () => { setForm(emptyForm); setEditingId(null); setModalOpen(true) }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const url = editingId ? `/api/contratos/${editingId}` : '/api/contratos'
      const res = await fetch(url, {
        method: editingId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (res.ok) { setModalOpen(false); fetchAll() }
    } catch (err) { console.error(err) }
    finally { setSaving(false) }
  }

  const handleCancel = async (id: string) => {
    try {
      await fetch(`/api/contratos/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'CANCELLED' }),
      })
      setCancelDialog(null)
      fetchAll()
    } catch (err) { console.error(err) }
  }

  const handleDelete = async (id: string) => {
    try {
      await fetch(`/api/contratos/${id}`, { method: 'DELETE' })
      setDeleteDialog(null)
      fetchAll()
    } catch (err) { console.error(err) }
  }

  if (loading) return <LoadingSpinner size="lg" />

  const availableProperties = properties.filter(p => p.status === 'AVAILABLE')

  const columns = [
    { key: 'property', label: 'Imóvel', render: (c: Contract) => <span className="font-medium text-gray-900">{c.property?.name}</span> },
    { key: 'tenant', label: 'Inquilino', render: (c: Contract) => c.tenant?.name },
    { key: 'rentValue', label: 'Aluguel', render: (c: Contract) => <span className="font-semibold">{formatCurrency(c.rentValue)}</span> },
    { key: 'startDate', label: 'Início', render: (c: Contract) => formatDate(c.startDate) },
    { key: 'endDate', label: 'Fim', render: (c: Contract) => formatDate(c.endDate) },
    { key: 'dueDay', label: 'Venc.', render: (c: Contract) => `Dia ${c.dueDay}` },
    { key: 'status', label: 'Status', render: (c: Contract) => <StatusBadge status={c.status} /> },
  ]

  return (
    <div className="animate-fadeIn">
      <Header title="Contratos" />
      <div className="p-4 lg:p-8">
        <div className="page-header">
          <div>
            <h1 className="page-title">Contratos</h1>
            <p className="text-gray-500 text-sm mt-1">{contracts.filter(c => c.status === 'ACTIVE').length} contrato(s) ativo(s)</p>
          </div>
          <button onClick={openCreate} className="btn-primary"><Plus size={18} /> Novo Contrato</button>
        </div>

        <DataTable columns={columns} data={contracts} searchPlaceholder="Buscar contrato..."
          actions={(c) => (
            <div className="flex items-center gap-1">
              {c.status === 'ACTIVE' && (
                <button onClick={() => setCancelDialog(c.id)} className="p-2 text-gray-500 hover:text-yellow-600 hover:bg-yellow-50 rounded-lg transition-colors" title="Cancelar contrato">
                  <XCircle size={16} />
                </button>
              )}
              <button onClick={() => setDeleteDialog(c.id)} className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
                <Trash2 size={16} />
              </button>
            </div>
          )}
        />
      </div>

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Novo Contrato" size="lg">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label-field">Imóvel *</label>
              <select name="propertyId" value={form.propertyId} onChange={handleChange} className="input-field" required>
                <option value="">Selecione um imóvel</option>
                {availableProperties.map(p => <option key={p.id} value={p.id}>{p.name} - {formatCurrency(p.rentValue)}</option>)}
              </select>
            </div>
            <div>
              <label className="label-field">Inquilino *</label>
              <select name="tenantId" value={form.tenantId} onChange={handleChange} className="input-field" required>
                <option value="">Selecione um inquilino</option>
                {tenants.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="label-field">Data Início *</label>
              <input name="startDate" type="date" value={form.startDate} onChange={handleChange} className="input-field" required />
            </div>
            <div>
              <label className="label-field">Data Fim *</label>
              <input name="endDate" type="date" value={form.endDate} onChange={handleChange} className="input-field" required />
            </div>
            <div>
              <label className="label-field">Dia Vencimento *</label>
              <select name="dueDay" value={form.dueDay} onChange={handleChange} className="input-field">
                {Array.from({ length: 28 }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="label-field">Valor Aluguel (R$) *</label>
              <input name="rentValue" type="number" step="0.01" value={form.rentValue} onChange={handleChange} className="input-field" required />
            </div>
            <div>
              <label className="label-field">Caução (R$)</label>
              <input name="deposit" type="number" step="0.01" value={form.deposit} onChange={handleChange} className="input-field" />
            </div>
            <div>
              <label className="label-field">Índice de Reajuste</label>
              <select name="adjustmentIndex" value={form.adjustmentIndex} onChange={handleChange} className="input-field">
                <option value="IGPM">IGP-M</option>
                <option value="IPCA">IPCA</option>
                <option value="INPC">INPC</option>
              </select>
            </div>
          </div>
          <div>
            <label className="label-field">Observações</label>
            <textarea name="notes" value={form.notes} onChange={handleChange} rows={3} className="input-field" />
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Salvando...' : 'Criar Contrato'}</button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog isOpen={!!cancelDialog} onClose={() => setCancelDialog(null)}
        onConfirm={() => cancelDialog && handleCancel(cancelDialog)}
        title="Cancelar Contrato" message="Tem certeza que deseja cancelar este contrato? O imóvel será liberado."
        confirmLabel="Cancelar Contrato" variant="warning" />

      <ConfirmDialog isOpen={!!deleteDialog} onClose={() => setDeleteDialog(null)}
        onConfirm={() => deleteDialog && handleDelete(deleteDialog)}
        title="Excluir Contrato" message="Tem certeza que deseja excluir este contrato?" confirmLabel="Excluir" />
    </div>
  )
}
