'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || ''

interface Persona {
  name: string
  vibe: string
  themes: string
  language: string
}

interface Config {
  enabled: boolean
  posts_per_day: number
  stories_per_day: number
  account_id: string
  is_ai_generated: boolean
  persona: Persona
}

interface VaultItem {
  id: string
  kind: 'photo' | 'carousel' | 'video'
  hint: string
  created_at: string
  files: string[]
}

interface HistoryEntry {
  id: string
  slot: string
  at: string
  status: 'completed' | 'failed' | 'skipped'
  kind?: string
  caption?: string
  error?: string
  reason?: string
}

const KIND_LABEL: Record<string, string> = {
  photo: '🖼️ Foto', carousel: '🎠 Carrossel', video: '🎬 Vídeo', story: '⭕ Story',
}

export default function InstagramPage() {
  const [config, setConfig] = useState<Config>({
    enabled: false, posts_per_day: 2, stories_per_day: 1,
    account_id: '', is_ai_generated: false,
    persona: { name: '', vibe: '', themes: '', language: 'Português' },
  })
  const [vaultItems, setVaultItems] = useState<VaultItem[]>([])
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [nextRuns, setNextRuns] = useState<{ feed: string | null; story: string | null }>({ feed: null, story: null })
  const [running, setRunning] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const fetchLive = useCallback(async () => {
    try {
      const [v, s, h] = await Promise.all([
        fetch(`${API}/api/instagram/vault`),
        fetch(`${API}/api/instagram/status`),
        fetch(`${API}/api/instagram/history`),
      ])
      if (v.ok) { const d = await v.json(); setVaultItems(d.items || []); setCounts(d.counts || {}) }
      if (s.ok) { const d = await s.json(); setRunning(d.running); setNextRuns({ feed: d.next_feed, story: d.next_story }) }
      if (h.ok) { const d = await h.json(); setHistory(d.history || []) }
    } catch { /* silencioso */ }
  }, [])

  useEffect(() => {
    fetch(`${API}/api/instagram/config`).then(r => r.ok ? r.json() : null).then(c => { if (c) setConfig(c) }).catch(() => {})
  }, [])

  useEffect(() => {
    fetchLive()
    const id = setInterval(fetchLive, 12000)
    return () => clearInterval(id)
  }, [fetchLive])

  const saveConfig = async () => {
    setSaveMsg(''); setError('')
    try {
      const res = await fetch(`${API}/api/instagram/config`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(config),
      })
      if (!res.ok) throw new Error(`Erro ${res.status}`)
      setSaveMsg('Configuração salva!'); setTimeout(() => setSaveMsg(''), 3000)
      fetchLive()
    } catch (e) { setError(`Falha ao salvar: ${e instanceof Error ? e.message : 'erro'}`) }
  }

  const upload = async (files: FileList) => {
    setUploading(true); setError('')
    try {
      const form = new FormData()
      Array.from(files).slice(0, 10).forEach(f => form.append('files', f))
      const res = await fetch(`${API}/api/instagram/vault`, { method: 'POST', body: form })
      if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || `Erro ${res.status}`) }
      fetchLive()
    } catch (e) { setError(`Falha no upload: ${e instanceof Error ? e.message : 'erro'}`) }
    finally { setUploading(false); if (fileInput.current) fileInput.current.value = '' }
  }

  const deleteItem = async (id: string) => {
    try { await fetch(`${API}/api/instagram/vault/${id}`, { method: 'DELETE' }); fetchLive() } catch { /* */ }
  }

  const postNow = async (slot: 'feed' | 'story') => {
    setError('')
    try {
      const form = new FormData(); form.append('slot', slot)
      const res = await fetch(`${API}/api/instagram/post-now`, { method: 'POST', body: form })
      const d = await res.json()
      if (!res.ok) throw new Error(d.detail || `Erro ${res.status}`)
      setSaveMsg(`Publicando ${slot === 'feed' ? 'no feed' : 'story'}...`); setTimeout(() => setSaveMsg(''), 3000)
      setTimeout(fetchLive, 2000)
    } catch (e) { setError(`${e instanceof Error ? e.message : 'erro'}`) }
  }

  const setPersona = (patch: Partial<Persona>) => setConfig(c => ({ ...c, persona: { ...c.persona, ...patch } }))
  const fmtDate = (iso: string) => new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Automação Instagram</h1>
        <p className="text-white/40 mt-1 text-sm">Publica do cofre de mídias na frequência definida, com legendas da persona.</p>
      </div>

      {/* Status */}
      <div className="bg-[#111] border border-white/10 rounded-xl p-4 flex items-center justify-between text-sm">
        <div className="flex items-center gap-3">
          <div className={`w-2.5 h-2.5 rounded-full ${running ? 'bg-amber-400 animate-pulse' : config.enabled ? 'bg-green-400' : 'bg-white/20'}`} />
          <span className="text-white/70">{running ? 'Publicando...' : config.enabled ? 'Automação ativa' : 'Automação pausada'}</span>
        </div>
        <div className="text-xs text-white/30 text-right">
          {nextRuns.feed && <div>Próx. post: {fmtDate(nextRuns.feed)}</div>}
          {nextRuns.story && <div>Próx. story: {fmtDate(nextRuns.story)}</div>}
        </div>
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-red-400 text-sm">{error}</div>}
      {saveMsg && <div className="bg-green-500/10 border border-green-500/20 rounded-lg px-4 py-3 text-green-400 text-sm">{saveMsg}</div>}

      {/* Cofre */}
      <div className="bg-[#111] border border-white/10 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white/70 uppercase tracking-wider">Cofre de mídias</h2>
          <span className="text-xs text-white/30">
            {counts.video || 0} vídeos · {counts.carousel || 0} carrosséis · {counts.photo || 0} fotos
          </span>
        </div>

        <input ref={fileInput} type="file" accept="image/jpeg,image/png,video/mp4,video/quicktime" multiple className="hidden"
          onChange={(e) => e.target.files?.length && upload(e.target.files)} />
        <button onClick={() => fileInput.current?.click()} disabled={uploading}
          className="w-full border-2 border-dashed border-white/15 hover:border-violet-500/40 rounded-lg py-4 text-white/40 text-sm transition-colors disabled:opacity-50">
          {uploading ? 'Enviando...' : 'Subir mídia (1 arquivo = foto/vídeo · 2+ arquivos = carrossel)'}
        </button>
        <p className="text-white/25 text-xs">JPEG/PNG ou MP4/MOV. Feed ideal 4:5 (1080×1350). Reels/Stories 9:16. Selecione 2+ arquivos juntos para um carrossel.</p>

        {vaultItems.length > 0 && (
          <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
            {vaultItems.map(it => (
              <div key={it.id} className="relative group aspect-square rounded-lg overflow-hidden bg-black/40 border border-white/10">
                {it.files[0]?.match(/\.(mp4|mov)$/i)
                  ? <video src={`${API}${it.files[0]}`} className="w-full h-full object-cover" muted />
                  : <img src={`${API}${it.files[0]}`} alt="" className="w-full h-full object-cover" />}
                <span className="absolute top-1 left-1 text-[10px] bg-black/70 rounded px-1 text-white/80">{KIND_LABEL[it.kind]?.split(' ')[0]}</span>
                {it.files.length > 1 && <span className="absolute top-1 right-1 text-[10px] bg-black/70 rounded px-1 text-white/80">{it.files.length}</span>}
                <button onClick={() => deleteItem(it.id)}
                  className="absolute inset-0 bg-red-900/70 opacity-0 group-hover:opacity-100 transition-opacity text-white text-xs flex items-center justify-center">
                  remover
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Postar agora */}
      <div className="bg-[#111] border border-white/10 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-3">Postar agora</h2>
        <div className="flex gap-3">
          <button onClick={() => postNow('feed')} disabled={running}
            className="flex-1 bg-violet-600 hover:bg-violet-700 disabled:opacity-40 text-white font-medium py-2.5 rounded-lg text-sm transition-colors">
            Publicar post
          </button>
          <button onClick={() => postNow('story')} disabled={running}
            className="flex-1 bg-white/10 hover:bg-white/15 disabled:opacity-40 text-white font-medium py-2.5 rounded-lg text-sm transition-colors">
            Publicar story
          </button>
        </div>
        <p className="text-white/25 text-xs mt-2">Publica imediatamente um item do cofre, sem esperar a agenda.</p>
      </div>

      {/* Configuração */}
      <div className="bg-[#111] border border-white/10 rounded-xl p-5 space-y-5">
        <h2 className="text-sm font-semibold text-white/70 uppercase tracking-wider">Configuração</h2>

        <div className="flex items-center justify-between">
          <div><p className="text-sm font-medium text-white">Automação ativa</p><p className="text-xs text-white/30 mt-0.5">Liga a publicação automática</p></div>
          <button onClick={() => setConfig(c => ({ ...c, enabled: !c.enabled }))}
            className={`relative w-11 h-6 rounded-full transition-colors ${config.enabled ? 'bg-violet-600' : 'bg-white/15'}`}>
            <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${config.enabled ? 'translate-x-5' : ''}`} />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-white/60 mb-2">Posts / dia</label>
            <input type="number" min={0} max={20} value={config.posts_per_day}
              onChange={(e) => setConfig(c => ({ ...c, posts_per_day: Math.max(0, Math.min(20, +e.target.value || 0)) }))}
              className="w-full bg-[#0a0a0a] border border-white/15 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-violet-500/50" />
          </div>
          <div>
            <label className="block text-sm font-medium text-white/60 mb-2">Stories / dia</label>
            <input type="number" min={0} max={20} value={config.stories_per_day}
              onChange={(e) => setConfig(c => ({ ...c, stories_per_day: Math.max(0, Math.min(20, +e.target.value || 0)) }))}
              className="w-full bg-[#0a0a0a] border border-white/15 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-violet-500/50" />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-white/60 mb-2">Instagram Account ID (do painel Zernio)</label>
          <input value={config.account_id} onChange={(e) => setConfig(c => ({ ...c, account_id: e.target.value }))}
            placeholder="account id da conta Business/Creator"
            className="w-full bg-[#0a0a0a] border border-white/15 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-violet-500/50" />
        </div>

        <div className="flex items-center justify-between">
          <div><p className="text-sm font-medium text-white">Rotular como IA</p><p className="text-xs text-white/30 mt-0.5">Marca posts como mídia gerada por IA</p></div>
          <button onClick={() => setConfig(c => ({ ...c, is_ai_generated: !c.is_ai_generated }))}
            className={`relative w-11 h-6 rounded-full transition-colors ${config.is_ai_generated ? 'bg-violet-600' : 'bg-white/15'}`}>
            <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${config.is_ai_generated ? 'translate-x-5' : ''}`} />
          </button>
        </div>

        {/* Persona */}
        <div className="border-t border-white/5 pt-4 space-y-3">
          <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider">Persona (gera as legendas)</h3>
          <input value={config.persona.name} onChange={(e) => setPersona({ name: e.target.value })} placeholder="Nome da persona"
            className="w-full bg-[#0a0a0a] border border-white/15 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-violet-500/50" />
          <textarea value={config.persona.vibe} onChange={(e) => setPersona({ vibe: e.target.value })} rows={3}
            placeholder="Tom de voz e identidade (ex: descontraída, direta, fala de bem-estar com bom humor, usa gírias leves...)"
            className="w-full bg-[#0a0a0a] border border-white/15 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-violet-500/50 resize-none" />
          <input value={config.persona.themes} onChange={(e) => setPersona({ themes: e.target.value })} placeholder="Temas/nicho (ex: fitness, receitas fit, motivação)"
            className="w-full bg-[#0a0a0a] border border-white/15 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-violet-500/50" />
        </div>

        <button onClick={saveConfig} className="w-full bg-violet-600 hover:bg-violet-700 text-white font-medium py-2.5 rounded-lg text-sm transition-colors">
          Salvar configuração
        </button>
      </div>

      {/* Histórico */}
      {history.length > 0 && (
        <div className="bg-[#111] border border-white/10 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-white/5"><h2 className="text-sm font-semibold text-white/70 uppercase tracking-wider">Histórico</h2></div>
          <div className="divide-y divide-white/5">
            {history.map(h => (
              <div key={h.id} className="px-5 py-3 flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                      h.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                      h.status === 'failed' ? 'bg-red-500/20 text-red-400' : 'bg-white/10 text-white/40'}`}>
                      {h.status === 'completed' ? 'Publicado' : h.status === 'failed' ? 'Falhou' : 'Pulado'}
                    </span>
                    <span className="text-xs text-white/30">{h.kind ? KIND_LABEL[h.kind] || h.kind : h.slot}</span>
                  </div>
                  <p className="text-sm text-white/70 truncate">{h.caption || h.error || h.reason || '—'}</p>
                </div>
                <span className="text-xs text-white/30 shrink-0">{fmtDate(h.at)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
