'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import Header from '@/components/layout/Header'
import { Save, User, Bell, Shield, Key } from 'lucide-react'

export default function ConfiguracoesPage() {
  const { data: session } = useSession()
  const [activeTab, setActiveTab] = useState('perfil')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const [profileForm, setProfileForm] = useState({
    name: session?.user?.name || '',
    email: session?.user?.email || '',
    phone: '',
  })

  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  })

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    // API call would go here
    setTimeout(() => { setSaving(false); setSaved(true); setTimeout(() => setSaved(false), 3000) }, 1000)
  }

  const tabs = [
    { id: 'perfil', label: 'Perfil', icon: User },
    { id: 'seguranca', label: 'Segurança', icon: Shield },
    { id: 'notificacoes', label: 'Notificações', icon: Bell },
  ]

  return (
    <div className="animate-fadeIn">
      <Header title="Configurações" />
      <div className="p-4 lg:p-8">
        <h1 className="page-title mb-6">Configurações</h1>

        <div className="flex flex-col lg:flex-row gap-6">
          {/* Sidebar Tabs */}
          <div className="lg:w-56 flex-shrink-0">
            <div className="card p-2 space-y-1">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                      activeTab === tab.id ? 'bg-primary-50 text-primary-700' : 'text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    <Icon size={18} />
                    {tab.label}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Content */}
          <div className="flex-1">
            {activeTab === 'perfil' && (
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Informações do Perfil</h3>
                <form onSubmit={handleSaveProfile} className="space-y-4 max-w-lg">
                  <div>
                    <label className="label-field">Nome Completo</label>
                    <input value={profileForm.name} onChange={(e) => setProfileForm({...profileForm, name: e.target.value})}
                      className="input-field" />
                  </div>
                  <div>
                    <label className="label-field">E-mail</label>
                    <input type="email" value={profileForm.email} onChange={(e) => setProfileForm({...profileForm, email: e.target.value})}
                      className="input-field" />
                  </div>
                  <div>
                    <label className="label-field">Telefone</label>
                    <input value={profileForm.phone} onChange={(e) => setProfileForm({...profileForm, phone: e.target.value})}
                      className="input-field" placeholder="(11) 99999-9999" />
                  </div>
                  <div className="flex items-center gap-3 pt-2">
                    <button type="submit" className="btn-primary" disabled={saving}>
                      <Save size={16} /> {saving ? 'Salvando...' : 'Salvar Alterações'}
                    </button>
                    {saved && <span className="text-green-600 text-sm font-medium">Salvo com sucesso!</span>}
                  </div>
                </form>
              </div>
            )}

            {activeTab === 'seguranca' && (
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Alterar Senha</h3>
                <form className="space-y-4 max-w-lg">
                  <div>
                    <label className="label-field">Senha Atual</label>
                    <input type="password" value={passwordForm.currentPassword}
                      onChange={(e) => setPasswordForm({...passwordForm, currentPassword: e.target.value})}
                      className="input-field" />
                  </div>
                  <div>
                    <label className="label-field">Nova Senha</label>
                    <input type="password" value={passwordForm.newPassword}
                      onChange={(e) => setPasswordForm({...passwordForm, newPassword: e.target.value})}
                      className="input-field" />
                  </div>
                  <div>
                    <label className="label-field">Confirmar Nova Senha</label>
                    <input type="password" value={passwordForm.confirmPassword}
                      onChange={(e) => setPasswordForm({...passwordForm, confirmPassword: e.target.value})}
                      className="input-field" />
                  </div>
                  <button type="submit" className="btn-primary">
                    <Key size={16} /> Alterar Senha
                  </button>
                </form>
              </div>
            )}

            {activeTab === 'notificacoes' && (
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Preferências de Notificação</h3>
                <div className="space-y-4 max-w-lg">
                  {[
                    { label: 'Pagamento recebido', desc: 'Receber notificação quando um aluguel for pago' },
                    { label: 'Cobrança atrasada', desc: 'Alertar quando uma cobrança ficar em atraso' },
                    { label: 'Saque processado', desc: 'Notificar quando um saque for concluído' },
                    { label: 'Contrato vencendo', desc: 'Alertar 30 dias antes do contrato vencer' },
                  ].map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{item.label}</p>
                        <p className="text-xs text-gray-500">{item.desc}</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" defaultChecked className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                      </label>
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
