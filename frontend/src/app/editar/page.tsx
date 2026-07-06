'use client'

import { useState, useRef } from 'react'
import VideoDrop from '@/components/VideoDrop'

const API = process.env.NEXT_PUBLIC_API_URL || ''

const fmt = (s: number) => {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

export default function EditarPage() {
  const [video, setVideo] = useState<File | null>(null)
  const [duration, setDuration] = useState(0)

  // corte
  const [start, setStart] = useState(0)
  const [end, setEnd] = useState(0)
  // iluminação
  const [brightness, setBrightness] = useState(0)
  const [contrast, setContrast] = useState(1)
  const [saturation, setSaturation] = useState(1)
  // qualidade
  const [upscale, setUpscale] = useState(0)

  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const videoRef = useRef<HTMLVideoElement>(null)

  const cssFilter = `brightness(${1 + brightness}) contrast(${contrast}) saturate(${saturation})`

  const onLoaded = (d: number) => { setDuration(d); setStart(0); setEnd(d) }

  const reset = (f: File | null) => {
    setVideo(f); setDuration(0); setStart(0); setEnd(0)
    setBrightness(0); setContrast(1); setSaturation(1); setUpscale(0)
    setStatus(''); setError('')
  }

  const seek = (t: number) => { if (videoRef.current) videoRef.current.currentTime = t }

  const submit = async () => {
    if (!video) return setError('Selecione um vídeo')
    setError(''); setStatus(''); setLoading(true)

    const form = new FormData()
    form.append('video', video)
    form.append('trim_start', String(start))
    form.append('trim_end', String(end < duration ? end : 0))
    form.append('brightness', String(brightness))
    form.append('contrast', String(contrast))
    form.append('saturation', String(saturation))
    form.append('upscale', String(upscale))

    try {
      const res = await fetch(`${API}/api/editor/process`, { method: 'POST', body: form })
      if (!res.ok) throw new Error()
      const data = await res.json()
      if (data.status === 'COMPLETED') {
        setLoading(false)
        setStatus('Vídeo pronto! Acesse a Biblioteca para baixar.')
        reset(null)
      } else {
        setStatus('Melhorando a qualidade...')
        poll(data.job_id)
      }
    } catch {
      setError('Erro ao processar. Tente novamente.')
      setLoading(false)
    }
  }

  const poll = (id: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/editor/local-jobs/${id}`)
        const data = await res.json()
        if (data.status === 'COMPLETED') {
          clearInterval(interval); setLoading(false)
          setStatus('Vídeo pronto! Acesse a Biblioteca para baixar.')
          reset(null)
        } else if (data.status === 'FAILED') {
          clearInterval(interval); setLoading(false)
          setError(data.error || 'Processamento falhou. Tente novamente.'); setStatus('')
        } else {
          const pct = data.percent || 0
          setStatus(pct > 0 ? `Melhorando a qualidade... ${pct}%` : 'Melhorando a qualidade...')
        }
      } catch { /* continua tentando */ }
    }, 3000)
  }

  const lightSliders = [
    { label: 'Brilho', value: brightness, set: setBrightness, min: -0.5, max: 0.5, step: 0.05, show: brightness.toFixed(2) },
    { label: 'Contraste', value: contrast, set: setContrast, min: 0.5, max: 2, step: 0.05, show: contrast.toFixed(2) },
    { label: 'Saturação', value: saturation, set: setSaturation, min: 0, max: 2, step: 0.05, show: saturation.toFixed(2) },
  ]

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Editar Vídeo</h1>
        <p className="text-white/40 mt-1">Faça todos os ajustes e exporte de uma vez só</p>
      </div>

      <div className="mb-6" style={{ filter: video ? cssFilter : undefined }}>
        <VideoDrop file={video} onChange={reset} videoRef={videoRef} onLoaded={onLoaded} />
      </div>

      {duration > 0 && (
        <div className="space-y-4 mb-6">
          {/* Corte */}
          <div className="bg-[#111] border border-white/10 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">✂️ Corte</h3>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-white/60">Início</span>
                  <button onClick={() => seek(start)} className="text-violet-400 hover:text-violet-300">{fmt(start)}</button>
                </div>
                <input type="range" min={0} max={duration} step={0.1} value={start}
                  onChange={(e) => { const v = Math.min(+e.target.value, end - 0.1); setStart(v); seek(v) }}
                  className="w-full accent-violet-500" />
              </div>
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-white/60">Fim</span>
                  <button onClick={() => seek(end)} className="text-violet-400 hover:text-violet-300">{fmt(end)}</button>
                </div>
                <input type="range" min={0} max={duration} step={0.1} value={end}
                  onChange={(e) => { const v = Math.max(+e.target.value, start + 0.1); setEnd(v); seek(v) }}
                  className="w-full accent-violet-500" />
              </div>
              <p className="text-white/30 text-xs text-center">Duração final: {fmt(end - start)}</p>
            </div>
          </div>

          {/* Iluminação */}
          <div className="bg-[#111] border border-white/10 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">💡 Iluminação <span className="text-white/30 font-normal text-xs">(prévia em tempo real)</span></h3>
            <div className="space-y-4">
              {lightSliders.map((s) => (
                <div key={s.label}>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-white/60">{s.label}</span>
                    <span className="text-violet-400 font-mono">{s.show}</span>
                  </div>
                  <input type="range" min={s.min} max={s.max} step={s.step} value={s.value}
                    onChange={(e) => s.set(+e.target.value)} className="w-full accent-violet-500" />
                </div>
              ))}
            </div>
          </div>

          {/* Qualidade */}
          <div className="bg-[#111] border border-white/10 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white mb-1 flex items-center gap-2">✨ Qualidade</h3>
            <p className="text-white/30 text-xs mb-4">Aumenta resolução, nitidez e limpa ruído (rápido, sem GPU)</p>
            <div className="flex gap-2">
              {[{ v: 0, l: 'Nenhum' }, { v: 2, l: '2x' }, { v: 4, l: '4x' }].map((o) => (
                <button key={o.v} onClick={() => setUpscale(o.v)}
                  className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    upscale === o.v ? 'bg-violet-600 text-white' : 'bg-white/5 text-white/50 hover:bg-white/10'
                  }`}>{o.l}</button>
              ))}
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-red-400 text-sm mb-4">{error}</div>
      )}
      {loading && (
        <div className="bg-violet-500/10 border border-violet-500/20 rounded-lg px-4 py-3 text-violet-400 text-sm flex items-center gap-3 mb-4">
          <div className="w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin shrink-0" />
          {status || 'Processando...'}
        </div>
      )}
      {!loading && status && (
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg px-4 py-3 text-green-400 text-sm mb-4">{status}</div>
      )}

      <button onClick={submit} disabled={loading || !video}
        className="w-full bg-violet-600 hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium py-3 rounded-xl transition-colors text-sm">
        {loading ? 'Processando...' : 'Exportar Vídeo'}
      </button>
    </div>
  )
}
