'use client'

import { useEffect, useState } from 'react'
import Header from '@/components/layout/Header'
import DataTable from '@/components/ui/DataTable'
import Modal from '@/components/ui/Modal'
import StatusBadge from '@/components/ui/StatusBadge'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { formatCurrency, formatDate } from '@/lib/utils'
import { Plus, CheckCircle, Trash2, ExternalLink, QrCode } from 'lucide-react'

interface Charge {
  id: string
  contractId: string
  description: string
  value: number
  netValue: number
  platformFee: number
  dueDate: string
  paymentDate?: string
  status: string
  invoiceUrl?: string
  bankSlipUrl?: string
  pixCode?: string
  contract?: {
    property?: { name: string }
    tenant?: { name: string }
  }
}

interface Contract {
  id: string
  rentValue: number
  property?: { name: string }
  tenant?: { name: string }
  status: string
}

export default function CobrancasPage() {
  const [charges, setCharges] = useState<Charge[]>([])
  const [contracts, setContracts] = useState<Contract[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [confirmDialog, setConfirmDialog] = useState<string | null>(null)
  const [deleteDialog, setDeleteDialog] = useState<string | null>(null)
  const [form, setForm] = useState({ contractId: '', description: 'Aluguel mensal', value: '', dueDate: '', billingType: 'BOLETO' })
  const [saving, setSaving] = useState(false)
  const [filter, setFilter] = useState<string>('ALL')

  const fetchData = async () => {
    try {
      const [ch, ct] = await Promise.all([
        fetch('/api/cobrancas').then(r => r.json()),
        fetch('/api/contratos').then(r => r.json()),
      ])
      setCharges(ch)
      setContracts(ct.filter((c: Contract) => c.status === 'ACTIVE'))
    } catch (err) { console.error(err) }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchData() }, [])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const newForm = { ...form, [e.target.name]: e.target.value }
    if (e.target.name === 'contractId') {
      const ct = contracts.find(c => c.id === e.target.value)
      if (ct) newForm.value = String(ct.rentValue)
    }
    setForm(newForm)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const res = await fetch('/api/cobrancas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (res.ok) { setModalOpen(false); fetchData(); setForm({ contractId: '', description: 'Aluguel mensal', value: '', dueDate: '', billingType: 'BOLETO' }) }
    } catch (err) { console.error(err) }
    finally { setSaving(false) }
  }

  const handleConfirmPayment = async (id: string) => {
    try {
      await fetch(`/api/cobrancas/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'CONFIRMED' }),
      })
      setConfirmDialog(null)
      fetchData()
    } catch (err) { console.error(err) }
  }

  const handleDelete = async (id: string) => {
    try {
      await fetch(`/api/cobrancas/${id}`, { method: 'DELETE' })
      setDeleteDialog(null)
      fetchData()
    } catch (err) { console.error(err) }
  }

  if (loading) return <LoadingSpinner size="lg" />

  const filteredCharges = filter === 'ALL' ? charges : charges.filter(c => c.status === filter)

  const columns = [
    { key: 'property', label: 'Imóvel', render: (c: Charge) => <span className="font-medium text-gray-900">{c.contract?.property?.name}</span> },
    { key: 'tenant', label: 'Inquilino', render: (c: Charge) => c.contract?.tenant?.name },
    { key: 'description', label: 'Descrição' },
    { key: 'value', label: 'Valor', render: (c: Charge) => <span className="font-semibold">{formatCurrency(c.value)}</span> },
    { key: 'netValue', label: 'Líquido', render: (c: Charge) => <span className="text-green-600 font-medium">{formatCurrency(c.netValue)}</span> },
    { key: 'dueDate', label: 'Vencimento', render: (c: Charge) => formatDate(c.dueDate) },
    { key: 'status', label: 'Status', render: (c: Charge) => <StatusBadge status={c.status} /> },
  ]

  return (
    <div className="animate-fadeIn">
      <Header title="Cobranças" />
      <div className="p-4 lg:p-8">
        <div className="page-header">
          <div>
            <h1 className="page-title">Cobranças</h1>
            <p className="text-gray-500 text-sm mt-1">{charges.length} cobrança(s)</p>
          </div>
          <div className="flex items-center gap-3">
            <select value={filter} onChange={(e) => setFilter(e.target.value)} className="input-field w-auto">
              <option value="ALL">Todas</option>
              <option value="PENDING">Pendentes</option>
              <option value="CONFIRMED">Confirmadas</option>
              <option value="OVERDUE">Atrasadas</option>
            </select>
            <button onClick={() => setModalOpen(true)} className="btn-primary"><Plus size={18} /> Nova Cobrança</button>
          </div>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-6">
          <div className="card bg-green-50 border-green-100">
            <p className="text-xs font-medium text-green-600 uppercase">Confirmadas</p>
            <p className="text-xl font-bold text-green-700 mt-1">
              {formatCurrency(charges.filter(c => c.status === 'CONFIRMED').reduce((sum, c) => sum + c.value, 0))}
            </p>
          </div>
          <div className="card bg-yellow-50 border-yellow-100">
            <p className="text-xs font-medium text-yellow-600 uppercase">Pendentes</p>
            <p className="text-xl font-bold text-yellow-700 mt-1">
              {formatCurrency(charges.filter(c => c.status === 'PENDING').reduce((sum, c) => sum + c.value, 0))}
            </p>
          </div>
          <div className="card bg-red-50 border-red-100">
            <p className="text-xs font-medium text-red-600 uppercase">Atrasadas</p>
            <p className="text-xl font-bold text-red-700 mt-1">
              {formatCurrency(charges.filter(c => c.status === 'OVERDUE').reduce((sum, c) => sum + c.value, 0))}
            </p>
          </div>
          <div className="card bg-blue-50 border-blue-100">
            <p className="text-xs font-medium text-blue-600 uppercase">Taxas Plataforma</p>
            <p className="text-xl font-bold text-blue-700 mt-1">
              {formatCurrency(charges.filter(c => c.status === 'CONFIRMED').reduce((sum, c) => sum + c.platformFee, 0))}
            </p>
          </div>
        </div>

        <DataTable columns={columns} data={filteredCharges} searchPlaceholder="Buscar cobrança..."
          actions={(c) => (
            <div className="flex items-center gap-1">
              {c.status === 'PENDING' && (
                <button onClick={() => setConfirmDialog(c.id)} className="p-2 text-gray-500 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors" title="Confirmar pagamento">
                  <CheckCircle size={16} />
                </button>
              )}
              {c.invoiceUrl && (
                <a href={c.invoiceUrl} target="_blank" rel="noopener noreferrer" className="p-2 text-gray-500 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors" title="Ver fatura">
                  <ExternalLink size={16} />
                </a>
              )}
              {c.status !== 'CONFIRMED' && (
                <button onClick={() => setDeleteDialog(c.id)} className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
                  <Trash2 size={16} />
                </button>
              )}
            </div>
          )}
        />
      </div>

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Nova Cobrança" size="md">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label-field">Contrato *</label>
            <select name="contractId" value={form.contractId} onChange={handleChange} className="input-field" required>
              <option value="">Selecione um contrato</option>
              {contracts.map(c => (
                <option key={c.id} value={c.id}>{c.property?.name} - {c.tenant?.name} ({formatCurrency(c.rentValue)})</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label-field">Valor (R$) *</label>
              <input name="value" type="number" step="0.01" value={form.value} onChange={handleChange} className="input-field" required />
            </div>
            <div>
              <label className="label-field">Vencimento *</label>
              <input name="dueDate" type="date" value={form.dueDate} onChange={handleChange} className="input-field" required />
            </div>
          </div>
          <div>
            <label className="label-field">Descrição</label>
            <input name="description" value={form.description} onChange={handleChange} className="input-field" />
          </div>
          <div>
            <label className="label-field">Forma de Pagamento</label>
            <select name="billingType" value={form.billingType} onChange={handleChange} className="input-field">
              <option value="BOLETO">Boleto</option>
              <option value="PIX">PIX</option>
              <option value="CREDIT_CARD">Cartão de Crédito</option>
              <option value="UNDEFINED">Indefinido</option>
            </select>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
            <strong>Taxa:</strong> R$ 20,00 por aluguel recebido. Valor líquido: {form.value ? formatCurrency(parseFloat(form.value) - 20) : 'R$ 0,00'}
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Criando...' : 'Criar Cobrança'}</button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog isOpen={!!confirmDialog} onClose={() => setConfirmDialog(null)}
        onConfirm={() => confirmDialog && handleConfirmPayment(confirmDialog)}
        title="Confirmar Pagamento" message="Confirmar que este pagamento foi recebido? O valor líquido será creditado na sua carteira."
        confirmLabel="Confirmar" variant="warning" />

      <ConfirmDialog isOpen={!!deleteDialog} onClose={() => setDeleteDialog(null)}
        onConfirm={() => deleteDialog && handleDelete(deleteDialog)}
        title="Excluir Cobrança" message="Tem certeza que deseja excluir esta cobrança?" confirmLabel="Excluir" />
    </div>
  )
}
