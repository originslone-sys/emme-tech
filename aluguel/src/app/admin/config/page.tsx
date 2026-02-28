'use client'

import { useState } from 'react'
import Header from '@/components/layout/Header'
import { Save, Server, CreditCard, Bell, Database } from 'lucide-react'

export default function AdminConfigPage() {
  const [activeTab, setActiveTab] = useState('geral')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const [config, setConfig] = useState({
    platformFee: '20.00',
    asaasApiKey: '',
    asaasEnvironment: 'sandbox',
    appName: 'AluguelPro',
    supportEmail: 'suporte@aluguelpro.com',
  })

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setTimeout(() => { setSaving(false); setSaved(true); setTimeout(() => setSaved(false), 3000) }, 1000)
  }

  const tabs = [
    { id: 'geral', label: 'Geral', icon: Server },
    { id: 'pagamento', label: 'Pagamento', icon: CreditCard },
    { id: 'sistema', label: 'Sistema', icon: Database },
  ]

  return (
    <div className="animate-fadeIn">
      <Header title="Configurações do Sistema" />
      <div className="p-4 lg:p-8">
        <h1 className="page-title mb-6">Configurações do Sistema</h1>

        <div className="flex flex-col lg:flex-row gap-6">
          <div className="lg:w-56 flex-shrink-0">
            <div className="card p-2 space-y-1">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                      activeTab === tab.id ? 'bg-primary-50 text-primary-700' : 'text-gray-600 hover:bg-gray-50'
                    }`}>
                    <Icon size={18} /> {tab.label}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="flex-1">
            {activeTab === 'geral' && (
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Configurações Gerais</h3>
                <form onSubmit={handleSave} className="space-y-4 max-w-lg">
                  <div>
                    <label className="label-field">Nome da Plataforma</label>
                    <input value={config.appName} onChange={(e) => setConfig({...config, appName: e.target.value})}
                      className="input-field" />
                  </div>
                  <div>
                    <label className="label-field">E-mail de Suporte</label>
                    <input type="email" value={config.supportEmail} onChange={(e) => setConfig({...config, supportEmail: e.target.value})}
                      className="input-field" />
                  </div>
                  <div className="flex items-center gap-3 pt-2">
                    <button type="submit" className="btn-primary" disabled={saving}>
                      <Save size={16} /> {saving ? 'Salvando...' : 'Salvar'}
                    </button>
                    {saved && <span className="text-green-600 text-sm font-medium">Salvo!</span>}
                  </div>
                </form>
              </div>
            )}

            {activeTab === 'pagamento' && (
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Configurações de Pagamento (Asaas)</h3>
                <form onSubmit={handleSave} className="space-y-4 max-w-lg">
                  <div>
                    <label className="label-field">Taxa por Aluguel Recebido (R$)</label>
                    <input type="number" step="0.01" value={config.platformFee}
                      onChange={(e) => setConfig({...config, platformFee: e.target.value})} className="input-field" />
                    <p className="text-xs text-gray-400 mt-1">Valor cobrado por cada aluguel confirmado</p>
                  </div>
                  <div>
                    <label className="label-field">API Key do Asaas</label>
                    <input type="password" value={config.asaasApiKey}
                      onChange={(e) => setConfig({...config, asaasApiKey: e.target.value})}
                      className="input-field" placeholder="$aact_..." />
                  </div>
                  <div>
                    <label className="label-field">Ambiente</label>
                    <select value={config.asaasEnvironment} onChange={(e) => setConfig({...config, asaasEnvironment: e.target.value})}
                      className="input-field">
                      <option value="sandbox">Sandbox (Teste)</option>
                      <option value="production">Produção</option>
                    </select>
                  </div>
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
                    <strong>Modelo de cobrança:</strong> R$ {config.platformFee} por aluguel recebido. Sem assinatura fixa.
                    O valor é descontado automaticamente quando o pagamento é confirmado.
                  </div>
                  <div className="flex items-center gap-3 pt-2">
                    <button type="submit" className="btn-primary" disabled={saving}>
                      <Save size={16} /> {saving ? 'Salvando...' : 'Salvar'}
                    </button>
                    {saved && <span className="text-green-600 text-sm font-medium">Salvo!</span>}
                  </div>
                </form>
              </div>
            )}

            {activeTab === 'sistema' && (
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Informações do Sistema</h3>
                <div className="space-y-3 max-w-lg">
                  {[
                    { label: 'Versão', value: '1.0.0' },
                    { label: 'Framework', value: 'Next.js 14' },
                    { label: 'Banco de Dados', value: 'PostgreSQL + Prisma' },
                    { label: 'Gateway de Pagamento', value: 'Asaas' },
                    { label: 'Autenticação', value: 'NextAuth.js (JWT)' },
                  ].map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                      <span className="text-sm text-gray-500">{item.label}</span>
                      <span className="text-sm font-medium text-gray-900">{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
