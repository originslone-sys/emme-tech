'use client'

import { useRef, useState } from 'react'
import Link from 'next/link'

const API = process.env.NEXT_PUBLIC_API_URL || ''

const STAGES: Record<string, string> = {
  starting: 'Iniciando...',
  scripting: 'Criando o roteiro viral com IA...',
  fetching: 'Buscando as cenas no Pexels...',
  rendering: 'Montando o vídeo...',
}

const FORMATS = [
  { id: '9:16', label: 'Vertical', sub: 'TikTok / Reels / Shorts' },
  { id: '1:1', label: 'Quadrado', sub: 'Feed' },
  { id: '16:9', label: 'Horizontal', sub: 'YouTube' },
]

const LANGUAGES = ['Português', 'English', 'Español']

export default function GerarPage() {
  const [topic, setTopic] = useState('')
  const [fmt, setFmt] = useState('9:16')
  const [duration, setDuration] = useState(30)
  const [language, setLanguage] = useState('Português')
  const [music, setMusic] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [stage, setStage] = useState('')
  const [progress, setProgress] = useState({ done: 0, total: 0, percent: 0 })
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const musicInput = useRef<HTMLInputElement>(null)

  const submit = async () => {
    if (!topic.trim()) return setError('Descreva o tema do vídeo')
    setError(''); setDone(false); setLoading(true); setStage('starting')
    setProgress({ done: 0, total: 0, percent: 0 })

    const form = new FormData()
    form.append('topic', topic.trim())
    form.append('fmt', fmt)
    form.append('duration', String(duration))
    form.append('language', language)
    if (music) form.append('music', music)

    try {
      const res = await fetch(`${API}/api/viral/generate`, { method: 'POST', body: form })
      if (!res.ok) throw new Error(`Servidor retornou ${res.status}`)
      const data = await res.json()
      poll(data.job_id)
    } catch (e) {
      setError(`Erro ao enviar: ${e instanceof Error ? e.message : 'falha de conexão'}`)
      setLoading(false)
    }
  }

  const poll = (id: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/viral/jobs/${id}`)
        const data = await res.json()
        setStage(data.stage)
        setProgress({ done: data.done || 0, total: data.total || 0, percent: data.percent || 0 })
        if (data.status === 'COMPLETED') {
          clearInterval(interval); setLoading(false); setDone(true)
          setTopic(''); setMusic(null)
        } else if (data.status === 'FAILED') {
          clearInterval(interval); setLoading(false)
          setError(data.error || 'Processamento falhou.'); setStage('')
        }
      } catch { /* continua tentando */ }
    }, 2500)
  }

  let stageLabel = STAGES[stage] || 'Processando...'
  if (stage === 'fetching' && progress.total) {
    stageLabel = `Buscando cenas (${progress.done}/${progress.total})...`
  } else if (stage === 'rendering' && progress.percent > 0) {
    stageLabel = `Montando o vídeo... ${progress.percent}%`
  }

  return (
    <div className="max-w-xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Gerar Vídeo Viral</h1>
        <p className="text-white/40 mt-1">
          Descreva um tema e a IA cria o roteiro, escolhe as cenas, adiciona legendas e música
        </p>
      </div>

      <div className="mb-5">
        <label className="block text-sm font-medium text-white/60 mb-2">Tema do vídeo</label>
        <textarea
          value={topic}
          onChange={(e) => { setTopic(e.target.value); setDone(false) }}
          rows={3}
          placeholder="Ex: 3 hábitos que mudam sua vida financeira / a história secreta do café / por que você acorda cansado"
          className="w-full bg-[#111] border border-white/15 rounded-xl px-4 py-3 text-white text-sm focus:border-violet-500/50 outline-none resize-none"
        />
      </div>

      <div className="bg-[#111] border border-white/10 rounded-xl p-5 mb-6 space-y-5">
        <div>
          <label className="block text-sm font-medium text-white/60 mb-2">Formato</label>
          <div className="grid grid-cols-3 gap-2">
            {FORMATS.map((f) => (
              <button key={f.id} onClick={() => setFmt(f.id)}
                className={`py-2.5 rounded-lg text-center transition-colors ${
                  fmt === f.id ? 'bg-violet-600 text-white' : 'bg-white/5 text-white/50 hover:bg-white/10'
                }`}>
                <div className="text-sm font-medium">{f.label}</div>
                <div className="text-[10px] opacity-70">{f.sub}</div>
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-white/60 mb-2">Duração</label>
          <div className="flex gap-2">
            {[15, 30, 45, 60].map((n) => (
              <button key={n} onClick={() => setDuration(n)}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                  duration === n ? 'bg-violet-600 text-white' : 'bg-white/5 text-white/50 hover:bg-white/10'
                }`}>{n}s</button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-white/60 mb-2">Idioma</label>
          <div className="flex gap-2">
            {LANGUAGES.map((l) => (
              <button key={l} onClick={() => setLanguage(l)}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                  language === l ? 'bg-violet-600 text-white' : 'bg-white/5 text-white/50 hover:bg-white/10'
                }`}>{l}</button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-white/60 mb-2">Música (opcional)</label>
          <input ref={musicInput} type="file" accept="audio/*" className="hidden"
            onChange={(e) => e.target.files?.[0] && setMusic(e.target.files[0])} />
          {music ? (
            <div className="flex items-center gap-3">
              <span className="text-violet-400">🎵</span>
              <span className="flex-1 text-white/50 text-xs truncate">{music.name}</span>
              <button onClick={() => setMusic(null)} className="text-red-400 text-sm">remover</button>
            </div>
          ) : (
            <button onClick={() => musicInput.current?.click()}
              className="w-full border-2 border-dashed border-white/15 hover:border-violet-500/40 rounded-lg py-3 text-white/30 text-xs transition-colors">
              Enviar uma trilha sua, ou deixe a IA escolher pelo clima do vídeo
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 mb-4">
          <p className="text-red-400 text-sm font-medium mb-1">Falha no processamento</p>
          <pre className="text-red-300/70 text-xs whitespace-pre-wrap break-words max-h-40 overflow-auto font-mono">{error}</pre>
        </div>
      )}
      {loading && (
        <div className="bg-violet-500/10 border border-violet-500/20 rounded-lg px-4 py-3 mb-4">
          <div className="flex items-center gap-3 text-violet-400 text-sm mb-2">
            <div className="w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin shrink-0" />
            {stageLabel}
          </div>
          {stage === 'rendering' && progress.percent > 0 && (
            <div className="w-full bg-white/10 rounded-full h-2 overflow-hidden">
              <div className="bg-violet-500 h-full transition-all duration-500" style={{ width: `${progress.percent}%` }} />
            </div>
          )}
        </div>
      )}
      {done && (
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg px-4 py-3 text-green-400 text-sm mb-4">
          Vídeo gerado! <Link href="/biblioteca" className="underline">Ver na Biblioteca</Link>
        </div>
      )}

      <button onClick={submit} disabled={loading || !topic.trim()}
        className="w-full bg-violet-600 hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium py-3 rounded-xl transition-colors text-sm">
        {loading ? 'Processando...' : 'Gerar Vídeo Viral'}
      </button>

      <p className="text-white/25 text-xs text-center mt-4">
        O roteiro é gerado por IA, as cenas vêm do Pexels (livres pra uso) e tudo é montado automaticamente.
      </p>
    </div>
  )
}
