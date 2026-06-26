'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'

const API = process.env.NEXT_PUBLIC_API_URL || ''

interface Config {
  enabled: boolean
  interval_minutes: number
  voice: 'feminina' | 'masculina'
  tiktok_account_id: string
  auto_publish: boolean
}

interface Status {
  running: boolean
  scheduler_active: boolean
  next_run: string | null
}

interface HistoryEntry {
  id: string
  started_at: string
  finished_at?: string
  status: 'running' | 'completed' | 'failed' | 'skipped'
  title?: string
  fact_key?: string
  subtheme?: string
  video_id?: string
  error?: string
  published?: { error?: string } | null
}

const SUBTHEME_LABELS: Record<string, string> = {
  'espaço': '🚀 Espaço',
  'corpo humano': '🫀 Corpo Humano',
  'oceano': '🌊 Oceano',
  'história': '📜 História',
  'animais': '🐾 Animais',
  'psicologia': '🧠 Psicologia',
  'comida': '🍕 Comida',
  'tecnologia': '💻 Tecnologia',
}

export default function AutomacaoPage() {
  const [config, setConfig] = useState<Config>({
    enabled: false,
    interval_minutes: 30,
    voice: 'feminina',
    tiktok_account_id: '',
    auto_publish: false,
  })
  const [status, setStatus] = useState<Status>({ running: false, scheduler_active: false, next_run: null })
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [saving, setSaving] = useState(false)
  const [running, setRunning] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const [error, setError] = useState('')

  // Status e histórico mudam no servidor — pode atualizar em loop sem problema.
  const fetchLive = useCallback(async () => {
    try {
      const [statusRes, histRes] = await Promise.all([
        fetch(`${API}/api/automation/status`),
        fetch(`${API}/api/automation/history`),
      ])
      if (statusRes.ok) setStatus(await statusRes.json())
      if (histRes.ok) {
        const d = await histRes.json()
        setHistory(d.history || [])
      }
    } catch {
      // silencioso
    }
  }, [])

  // A config carrega UMA vez ao abrir. Não pode ser sobrescrita pelo polling,
  // senão apaga as alterações que o usuário fez antes de salvar.
  useEffect(() => {
    fetch(`${API}/api/automation/config`)
      .then((r) => (r.ok ? r.json() : null))
      .then((cfg) => { if (cfg) setConfig(cfg) })
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetchLive()
    const id = setInterval(fetchLive, 10000)
    return () => clearInterval(id)
  }, [fetchLive])

  const saveConfig = async () => {
    setSaving(true)
    setSaveMsg('')
    setError('')
    try {
      const res = await fetch(`${API}/api/automation/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      if (!res.ok) throw new Error(`Erro ${res.status}`)
      setSaveMsg('Configuração salva!')
      await fetchLive()
      setTimeout(() => setSaveMsg(''), 3000)
    } catch (e) {
      setError(`Falha ao salvar: ${e instanceof Error ? e.message : 'erro'}`)
    } finally {
      setSaving(false)
    }
  }

  const runNow = async () => {
    setRunning(true)
    setError('')
    try {
      const res = await fetch(`${API}/api/automation/run`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `Erro ${res.status}`)
      await fetchLive()
    } catch (e) {
      setError(`${e instanceof Error ? e.message : 'erro'}`)
    } finally {
      setRunning(false)
    }
  }

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Automação TikTok</h1>
        <p className="text-white/40 mt-1 text-sm">
          Gera e publica vídeos de curiosidades automaticamente. Pexels + Pixabay + IA.
        </p>
      </div>

      {/* Status */}
      <div className="bg-[#111] border border-white/10 rounded-xl p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-2.5 h-2.5 rounded-full ${status.running ? 'bg-amber-400 animate-pulse' : status.scheduler_active ? 'bg-green-400' : 'bg-white/20'}`} />
          <span className="text-sm text-white/70">
            {status.running ? 'Gerando agora...' : status.scheduler_active ? 'Automação ativa' : 'Automação pausada'}
          </span>
        </div>
        {status.next_run && !status.running && (
          <span className="text-xs text-white/30">
            Próximo: {formatDate(status.next_run)}
          </span>
        )}
      </div>

      {/* Configuração */}
      <div className="bg-[#111] border border-white/10 rounded-xl p-5 space-y-5">
        <h2 className="text-sm font-semibold text-white/70 uppercase tracking-wider">Configuração</h2>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-white">Automação ativa</p>
            <p className="text-xs text-white/30 mt-0.5">Liga o agendamento automático</p>
          </div>
          <button
            onClick={() => setConfig(c => ({ ...c, enabled: !c.enabled }))}
            className={`relative w-11 h-6 rounded-full transition-colors ${config.enabled ? 'bg-violet-600' : 'bg-white/15'}`}
          >
            <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${config.enabled ? 'translate-x-5' : ''}`} />
          </button>
        </div>

        <div>
          <label className="block text-sm font-medium text-white/60 mb-2">
            Intervalo entre vídeos
          </label>
          <div className="flex gap-2">
            {[15, 30, 60, 120].map((n) => (
              <button
                key={n}
                onClick={() => setConfig(c => ({ ...c, interval_minutes: n }))}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                  config.interval_minutes === n
                    ? 'bg-violet-600 text-white'
                    : 'bg-white/5 text-white/50 hover:bg-white/10'
                }`}
              >
                {n < 60 ? `${n}min` : `${n / 60}h`}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-white/60 mb-2">Voz da narração</label>
          <div className="flex gap-2">
            {(['feminina', 'masculina'] as const).map((v) => (
              <button
                key={v}
                onClick={() => setConfig(c => ({ ...c, voice: v }))}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors capitalize ${
                  config.voice === v ? 'bg-violet-600 text-white' : 'bg-white/5 text-white/50 hover:bg-white/10'
                }`}
              >
                {v}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <div>
              <p className="text-sm font-medium text-white">Publicar no TikTok</p>
              <p className="text-xs text-white/30 mt-0.5">Via Zernio API (requer account ID)</p>
            </div>
            <button
              onClick={() => setConfig(c => ({ ...c, auto_publish: !c.auto_publish }))}
              className={`relative w-11 h-6 rounded-full transition-colors ${config.auto_publish ? 'bg-violet-600' : 'bg-white/15'}`}
            >
              <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${config.auto_publish ? 'translate-x-5' : ''}`} />
            </button>
          </div>
          {config.auto_publish && (
            <input
              value={config.tiktok_account_id}
              onChange={(e) => setConfig(c => ({ ...c, tiktok_account_id: e.target.value }))}
              placeholder="TikTok Account ID (do painel Zernio)"
              className="w-full bg-[#0a0a0a] border border-white/15 rounded-lg px-3 py-2 text-white text-sm focus:border-violet-500/50 outline-none"
            />
          )}
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 text-red-400 text-xs">
            {error}
          </div>
        )}

        <div className="flex gap-3 pt-1">
          <button
            onClick={saveConfig}
            disabled={saving}
            className="flex-1 bg-violet-600 hover:bg-violet-700 disabled:opacity-40 text-white font-medium py-2.5 rounded-lg text-sm transition-colors"
          >
            {saving ? 'Salvando...' : saveMsg || 'Salvar configuração'}
          </button>
          <button
            onClick={runNow}
            disabled={running || status.running}
            className="flex-1 bg-white/10 hover:bg-white/15 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium py-2.5 rounded-lg text-sm transition-colors"
          >
            {running || status.running ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-3.5 h-3.5 border-2 border-white/50 border-t-white rounded-full animate-spin" />
                Gerando...
              </span>
            ) : 'Gerar agora'}
          </button>
        </div>
      </div>

      {/* Histórico */}
      {history.length > 0 && (
        <div className="bg-[#111] border border-white/10 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-white/5">
            <h2 className="text-sm font-semibold text-white/70 uppercase tracking-wider">Histórico</h2>
          </div>
          <div className="divide-y divide-white/5">
            {history.map((entry) => (
              <div key={entry.id} className="px-5 py-3.5">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                        entry.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                        entry.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                        entry.status === 'running' ? 'bg-amber-500/20 text-amber-400' :
                        'bg-white/10 text-white/40'
                      }`}>
                        {entry.status === 'completed' ? 'Concluído' :
                         entry.status === 'failed' ? 'Falhou' :
                         entry.status === 'running' ? 'Executando' : 'Ignorado'}
                      </span>
                      {entry.subtheme && (
                        <span className="text-xs text-white/30">
                          {SUBTHEME_LABELS[entry.subtheme] || entry.subtheme}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-white/80 truncate">
                      {entry.title || entry.error || 'Sem título'}
                    </p>
                    {entry.fact_key && (
                      <p className="text-xs text-white/30 mt-0.5 font-mono">{entry.fact_key}</p>
                    )}
                    {entry.published && !entry.published.error && (
                      <p className="text-xs text-green-400/70 mt-0.5">Publicado no TikTok</p>
                    )}
                    {entry.published?.error && (
                      <p className="text-xs text-amber-400/70 mt-0.5">Publicação falhou: {entry.published.error}</p>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs text-white/30">{formatDate(entry.started_at)}</p>
                    {entry.video_id && entry.status === 'completed' && (
                      <Link
                        href="/biblioteca"
                        className="text-xs text-violet-400 hover:text-violet-300 mt-1 block"
                      >
                        Ver vídeo →
                      </Link>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {history.length === 0 && (
        <div className="text-center py-10 text-white/25 text-sm">
          Nenhuma execução ainda. Clique em &ldquo;Gerar agora&rdquo; para testar.
        </div>
      )}

      <p className="text-white/20 text-xs text-center pb-4">
        Curiosidades geradas por IA (DeepSeek) · Vídeos: Pexels, Pixabay e Kling AI · Voz: ElevenLabs
      </p>
    </div>
  )
}
