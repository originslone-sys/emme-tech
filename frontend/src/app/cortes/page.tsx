'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import VideoDrop from '@/components/VideoDrop'
import ChannelNameInput, { rememberChannelName } from '@/components/ChannelNameInput'
import { useJobs } from '@/lib/jobs'

const API = process.env.NEXT_PUBLIC_API_URL || ''

const STAGES: Record<string, string> = {
  starting: 'Iniciando...',
  downloading: 'Baixando o vídeo...',
  transcribing: 'Transcrevendo o áudio...',
  analyzing: 'Analisando os melhores momentos com IA...',
  rendering: 'Renderizando os cortes...',
}

export default function CortesPage() {
  const [mode, setMode] = useState<'upload' | 'youtube'>('upload')
  const [video, setVideo] = useState<File | null>(null)
  const [url, setUrl] = useState('')
  const [numClips, setNumClips] = useState(3)
  const [minDuration, setMinDuration] = useState(15)
  const [language, setLanguage] = useState('pt')
  const [banner, setBanner] = useState<File | null>(null)
  const [showTitle, setShowTitle] = useState(true)
  const [channelName, setChannelName] = useState('')
  const [error, setError] = useState('')
  const [trackedId, setTrackedId] = useState<string | null>(null)
  const [uploadPct, setUploadPct] = useState<number | null>(null)
  const bannerInput = useRef<HTMLInputElement>(null)
  const { jobs, addJob } = useJobs()

  // Recupera um job em andamento ao abrir/voltar à página
  useEffect(() => {
    if (!trackedId) {
      const active = jobs.find((j) => j.type === 'clips' && j.status === 'processing')
      if (active) setTrackedId(active.id)
    }
  }, [jobs, trackedId])

  const job = jobs.find((j) => j.id === trackedId)
  const loading = job?.status === 'processing'
  const done = job?.status === 'COMPLETED'
  const stage = job?.stage || ''
  const progress = { done: job?.done || 0, total: job?.total || 0 }
  const jobError = job?.status === 'FAILED' ? (job.error || 'Processamento falhou.') : ''

  const submit = async () => {
    if (mode === 'upload' && !video) return setError('Selecione um vídeo')
    if (mode === 'youtube' && !url.trim()) return setError('Cole o link do vídeo')
    setError('')

    try {
      // Vídeo grande: envia em pedaços (chunks) para não estourar o limite de
      // tamanho de requisição do servidor. Pedaços de 8 MB enviados em ordem.
      let uploadId: string | null = null
      if (mode === 'upload' && video) {
        setUploadPct(0)
        uploadId = crypto.randomUUID()
        const CHUNK = 2 * 1024 * 1024  // 2 MB — bem abaixo de qualquer limite de proxy
        const totalChunks = Math.ceil(video.size / CHUNK)
        for (let i = 0; i < totalChunks; i++) {
          const blob = video.slice(i * CHUNK, (i + 1) * CHUNK)

          let ok = false
          for (let attempt = 0; attempt < 4 && !ok; attempt++) {
            try {
              // Envia como binário puro (sem multipart) para evitar limites de proxy
              const r = await fetch(`${API}/api/clips/upload-chunk`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/octet-stream',
                  'X-Upload-Id': uploadId,
                  'X-Chunk-Index': String(i),
                },
                body: blob,
              })
              if (!r.ok) {
                let detail = `Erro ${r.status}`
                try { const j = await r.json(); if (j.detail) detail = j.detail } catch {}
                throw new Error(detail)
              }
              ok = true
            } catch (err) {
              if (attempt === 3) throw err
              await new Promise((res) => setTimeout(res, 800 * Math.pow(2, attempt)))
            }
          }
          setUploadPct(Math.round(((i + 1) / totalChunks) * 100))
        }
      }

      const form = new FormData()
      if (uploadId && video) {
        form.append('upload_id', uploadId)
        const dot = video.name.lastIndexOf('.')
        form.append('video_ext', dot >= 0 ? video.name.slice(dot).toLowerCase() : '.mp4')
      }
      if (mode === 'youtube') form.append('youtube_url', url.trim())
      form.append('num_clips', String(numClips))
      form.append('min_duration', String(minDuration))
      if (language) form.append('language', language)
      form.append('show_title', showTitle ? '1' : '0')
      if (channelName.trim()) {
        form.append('channel_name', channelName.trim())
        rememberChannelName(channelName)
      }
      if (banner) form.append('banner', banner)

      const res = await fetch(`${API}/api/clips/generate`, { method: 'POST', body: form })
      setUploadPct(null)
      if (!res.ok) {
        let detail = `Erro ${res.status}`
        try { const j = await res.json(); if (j.detail) detail = j.detail } catch {}
        throw new Error(detail)
      }
      const data = await res.json()
      const label = mode === 'youtube' ? url.trim() : (video?.name || 'Cortes')
      addJob(data.job_id, 'clips', label)
      setTrackedId(data.job_id)
      setVideo(null); setUrl(''); setBanner(null)
    } catch (e: unknown) {
      setUploadPct(null)
      const msg = e instanceof Error ? e.message : 'Erro desconhecido'
      setError(msg)
    }
  }

  const busy = uploadPct !== null || loading

  const stageLabel = stage === 'rendering' && progress.total
    ? `Renderizando cortes (${progress.done}/${progress.total})...`
    : stage === 'analyzing' && progress.total > 1
    ? `Analisando o vídeo (bloco ${progress.done}/${progress.total})...`
    : STAGES[stage] || 'Processando...'

  return (
    <div className="max-w-xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Cortes Virais</h1>
        <p className="text-white/40 mt-1">Transforme um vídeo longo em cortes prontos pra TikTok, Reels e Shorts</p>
      </div>

      <div className="flex gap-2 mb-5">
        {(['upload', 'youtube'] as const).map((m) => (
          <button key={m} onClick={() => setMode(m)}
            className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              mode === m ? 'bg-violet-600 text-white' : 'bg-white/5 text-white/50 hover:bg-white/10'
            }`}>
            {m === 'upload' ? 'Enviar vídeo' : 'Link de vídeo'}
          </button>
        ))}
      </div>

      {mode === 'upload' ? (
        <div className="mb-6">
          <VideoDrop file={video} onChange={(f) => setVideo(f)} />
          {video && video.size > 1024 * 1024 * 1024 && (
            <div className="mt-2 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2 text-amber-300/90 text-xs">
              Este arquivo tem {(video.size / 1024 / 1024 / 1024).toFixed(1)} GB. O envio é feito
              em partes, então arquivos grandes funcionam — mas o upload pode demorar dependendo
              da sua conexão. Não feche a aba até o envio chegar a 100%.
            </div>
          )}
        </div>
      ) : (
        <div className="mb-6">
          <input
            type="url" value={url} onChange={(e) => setUrl(e.target.value)}
            placeholder="https://vimeo.com/... · YouTube, TikTok, X, ou link direto .mp4"
            className="w-full bg-[#111] border border-white/15 rounded-xl px-4 py-3 text-white text-sm focus:border-violet-500/50 outline-none"
          />
          <p className="text-white/40 text-xs mt-2">
            Funciona com Vimeo, Dailymotion, TikTok, X e links diretos. O YouTube
            costuma exigir verificação anti-bot — se falhar, use outro link ou envie o arquivo.
          </p>
        </div>
      )}

      <div className="bg-[#111] border border-white/10 rounded-xl p-5 mb-6 space-y-5">
        <div>
          <label className="block text-sm font-medium text-white/60 mb-2">Idioma do vídeo</label>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
            {[
              { code: 'pt', label: 'Português' },
              { code: 'en', label: 'Inglês' },
              { code: 'es', label: 'Espanhol' },
              { code: 'fr', label: 'Francês' },
              { code: 'de', label: 'Alemão' },
              { code: '', label: 'Auto' },
            ].map(({ code, label }) => (
              <button key={code} onClick={() => setLanguage(code)}
                className={`py-2 rounded-lg text-sm font-medium transition-colors ${
                  language === code ? 'bg-violet-600 text-white' : 'bg-white/5 text-white/50 hover:bg-white/10'
                }`}>{label}</button>
            ))}
          </div>
          <p className="text-white/30 text-xs mt-2">
            Defina o idioma do áudio para evitar erros na transcrição. Use "Auto" só se não souber.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-white/60 mb-2">Quantos cortes gerar</label>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
            {[3, 5, 10, 15, 20].map((n) => (
              <button key={n} onClick={() => setNumClips(n)}
                className={`py-2 rounded-lg text-sm font-medium transition-colors ${
                  numClips === n ? 'bg-violet-600 text-white' : 'bg-white/5 text-white/50 hover:bg-white/10'
                }`}>{n}</button>
            ))}
            <input
              type="number" min={1} max={30} value={numClips}
              onChange={(e) => setNumClips(Math.max(1, Math.min(30, Number(e.target.value) || 1)))}
              className="py-2 px-2 rounded-lg text-sm font-medium text-center bg-white/5 text-white/80 border border-white/10 focus:border-violet-500/50 outline-none w-full"
              aria-label="Quantidade personalizada"
            />
          </div>
          <p className="text-white/30 text-xs mt-2">
            Para vídeos longos (filmes, podcasts, aulas) você pode gerar até 30 cortes de uma vez. Quanto mais cortes, mais tempo leva.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-white/60 mb-2">Duração mínima de cada corte</label>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
            {[15, 30, 45, 60, 90].map((s) => (
              <button key={s} onClick={() => setMinDuration(s)}
                className={`py-2 rounded-lg text-sm font-medium transition-colors ${
                  minDuration === s ? 'bg-violet-600 text-white' : 'bg-white/5 text-white/50 hover:bg-white/10'
                }`}>{s}s</button>
            ))}
            <input
              type="number" min={5} max={120} value={minDuration}
              onChange={(e) => setMinDuration(Math.max(5, Math.min(120, Number(e.target.value) || 5)))}
              className="py-2 px-2 rounded-lg text-sm font-medium text-center bg-white/5 text-white/80 border border-white/10 focus:border-violet-500/50 outline-none w-full"
              aria-label="Duração mínima personalizada (segundos)"
            />
          </div>
          <p className="text-white/30 text-xs mt-2">
            Cada corte terá pelo menos esse tempo. Ideal: 15-30s para Shorts/Reels, 60s+ para cortes mais longos.
          </p>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-sm font-medium text-white/60">Título no topo</label>
            <button onClick={() => setShowTitle(!showTitle)}
              className={`relative w-11 h-6 rounded-full transition-colors ${showTitle ? 'bg-violet-600' : 'bg-white/15'}`}>
              <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${showTitle ? 'translate-x-5' : ''}`} />
            </button>
          </div>
          <p className="text-white/30 text-xs">Exibe o título do corte fixo no topo do vídeo.</p>
        </div>

        <ChannelNameInput value={channelName} onChange={setChannelName} />

        <div>
          <label className="block text-sm font-medium text-white/60 mb-2">Banner (opcional)</label>
          <input ref={bannerInput} type="file" accept="image/*" className="hidden"
            onChange={(e) => e.target.files?.[0] && setBanner(e.target.files[0])} />
          {banner ? (
            <div className="flex items-center gap-3">
              <img src={URL.createObjectURL(banner)} className="h-12 rounded-lg" alt="" />
              <span className="flex-1 text-white/50 text-xs truncate">{banner.name}</span>
              <button onClick={() => setBanner(null)} className="text-red-400 text-sm">remover</button>
            </div>
          ) : (
            <button onClick={() => bannerInput.current?.click()}
              className="w-full border-2 border-dashed border-white/15 hover:border-violet-500/40 rounded-lg py-3 text-white/30 text-xs transition-colors">
              Clique para adicionar uma imagem fixa no rodapé dos cortes
            </button>
          )}
        </div>
      </div>

      {(error || jobError) && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-red-400 text-sm mb-4">{error || jobError}</div>
      )}
      {uploadPct !== null && (
        <div className="bg-violet-500/10 border border-violet-500/20 rounded-lg px-4 py-3 text-violet-400 text-sm mb-4">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin shrink-0" />
            Enviando vídeo... {uploadPct}%
          </div>
          <div className="w-full bg-white/10 rounded-full h-1.5 overflow-hidden">
            <div className="bg-violet-500 h-full transition-all duration-300" style={{ width: `${uploadPct}%` }} />
          </div>
        </div>
      )}
      {loading && (
        <div className="bg-violet-500/10 border border-violet-500/20 rounded-lg px-4 py-3 text-violet-400 text-sm flex items-center gap-3 mb-4">
          <div className="w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin shrink-0" />
          {stageLabel}
        </div>
      )}
      {done && (
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg px-4 py-3 text-green-400 text-sm mb-4">
          Cortes gerados! <Link href="/biblioteca" className="underline">Ver na Biblioteca</Link>
        </div>
      )}

      <button onClick={submit} disabled={busy}
        className="w-full bg-violet-600 hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium py-3 rounded-xl transition-colors text-sm">
        {uploadPct !== null ? `Enviando... ${uploadPct}%` : loading ? 'Processando...' : 'Gerar Cortes'}
      </button>

      <p className="text-white/25 text-xs text-center mt-4">
        Pode levar alguns minutos dependendo da duração do vídeo.
      </p>
    </div>
  )
}
