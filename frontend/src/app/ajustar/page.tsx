'use client'

import { useState } from 'react'
import VideoDrop from '@/components/VideoDrop'

const API = process.env.NEXT_PUBLIC_API_URL || ''

export default function AjustarPage() {
  const [video, setVideo] = useState<File | null>(null)
  const [brightness, setBrightness] = useState(0)
  const [contrast, setContrast] = useState(1)
  const [saturation, setSaturation] = useState(1)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')

  const cssFilter = `brightness(${1 + brightness}) contrast(${contrast}) saturate(${saturation})`

  const submit = async () => {
    if (!video) return setError('Selecione um vídeo')
    setError(''); setStatus(''); setLoading(true)

    const form = new FormData()
    form.append('video', video)
    form.append('brightness', String(brightness))
    form.append('contrast', String(contrast))
    form.append('saturation', String(saturation))

    try {
      const res = await fetch(`${API}/api/editor/adjust`, { method: 'POST', body: form })
      if (!res.ok) throw new Error()
      await res.json()
      setStatus('Vídeo ajustado! Acesse a Biblioteca para baixar.')
      setVideo(null)
    } catch {
      setError('Erro ao ajustar. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  const sliders = [
    { label: 'Brilho', value: brightness, set: setBrightness, min: -0.5, max: 0.5, step: 0.05, show: brightness.toFixed(2) },
    { label: 'Contraste', value: contrast, set: setContrast, min: 0.5, max: 2, step: 0.05, show: contrast.toFixed(2) },
    { label: 'Saturação', value: saturation, set: setSaturation, min: 0, max: 2, step: 0.05, show: saturation.toFixed(2) },
  ]

  return (
    <div className="max-w-xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Iluminação</h1>
        <p className="text-white/40 mt-1">Ajuste brilho, contraste e saturação (prévia em tempo real)</p>
      </div>

      <div className="mb-6" style={{ filter: video ? cssFilter : undefined }}>
        <VideoDrop file={video} onChange={(f) => { setVideo(f); setStatus('') }} />
      </div>

      {video && (
        <div className="bg-[#111] border border-white/10 rounded-xl p-5 mb-6 space-y-5">
          {sliders.map((s) => (
            <div key={s.label}>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-white/60">{s.label}</span>
                <span className="text-violet-400 font-mono">{s.show}</span>
              </div>
              <input
                type="range" min={s.min} max={s.max} step={s.step} value={s.value}
                onChange={(e) => s.set(+e.target.value)}
                className="w-full accent-violet-500"
              />
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-red-400 text-sm mb-4">{error}</div>
      )}
      {loading && (
        <div className="bg-violet-500/10 border border-violet-500/20 rounded-lg px-4 py-3 text-violet-400 text-sm flex items-center gap-3 mb-4">
          <div className="w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin shrink-0" />
          Aplicando ajustes...
        </div>
      )}
      {!loading && status && (
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg px-4 py-3 text-green-400 text-sm mb-4">{status}</div>
      )}

      <button
        onClick={submit}
        disabled={loading || !video}
        className="w-full bg-violet-600 hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium py-3 rounded-xl transition-colors text-sm"
      >
        {loading ? 'Processando...' : 'Aplicar Ajustes'}
      </button>
    </div>
  )
}
