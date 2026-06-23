'use client'

import { useState, useRef } from 'react'
import VideoDrop from '@/components/VideoDrop'

const API = process.env.NEXT_PUBLIC_API_URL || ''

const fmt = (s: number) => {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

export default function CortarPage() {
  const [video, setVideo] = useState<File | null>(null)
  const [duration, setDuration] = useState(0)
  const [start, setStart] = useState(0)
  const [end, setEnd] = useState(0)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const videoRef = useRef<HTMLVideoElement>(null)

  const onLoaded = (d: number) => {
    setDuration(d)
    setStart(0)
    setEnd(d)
  }

  const reset = (f: File | null) => {
    setVideo(f); setDuration(0); setStart(0); setEnd(0); setStatus(''); setError('')
  }

  const seek = (t: number) => {
    if (videoRef.current) videoRef.current.currentTime = t
  }

  const submit = async () => {
    if (!video) return setError('Selecione um vídeo')
    if (end <= start) return setError('O fim deve ser maior que o início')
    setError(''); setStatus(''); setLoading(true)

    const form = new FormData()
    form.append('video', video)
    form.append('start', String(start))
    form.append('end', String(end))

    try {
      const res = await fetch(`${API}/api/editor/trim`, { method: 'POST', body: form })
      if (!res.ok) throw new Error()
      await res.json()
      setStatus('Vídeo cortado! Acesse a Biblioteca para baixar.')
      reset(null)
    } catch {
      setError('Erro ao cortar. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Cortar</h1>
        <p className="text-white/40 mt-1">Mantenha apenas o trecho que você quer</p>
      </div>

      <div className="mb-6">
        <VideoDrop file={video} onChange={reset} videoRef={videoRef} onLoaded={onLoaded} />
      </div>

      {duration > 0 && (
        <div className="bg-[#111] border border-white/10 rounded-xl p-5 mb-6 space-y-5">
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-white/60">Início</span>
              <button onClick={() => seek(start)} className="text-violet-400 hover:text-violet-300">
                {fmt(start)}
              </button>
            </div>
            <input
              type="range" min={0} max={duration} step={0.1} value={start}
              onChange={(e) => { const v = Math.min(+e.target.value, end - 0.1); setStart(v); seek(v) }}
              className="w-full accent-violet-500"
            />
          </div>
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-white/60">Fim</span>
              <button onClick={() => seek(end)} className="text-violet-400 hover:text-violet-300">
                {fmt(end)}
              </button>
            </div>
            <input
              type="range" min={0} max={duration} step={0.1} value={end}
              onChange={(e) => { const v = Math.max(+e.target.value, start + 0.1); setEnd(v); seek(v) }}
              className="w-full accent-violet-500"
            />
          </div>
          <p className="text-white/30 text-xs text-center">
            Duração final: {fmt(end - start)}
          </p>
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-red-400 text-sm mb-4">{error}</div>
      )}
      {!loading && status && (
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg px-4 py-3 text-green-400 text-sm mb-4">{status}</div>
      )}

      <button
        onClick={submit}
        disabled={loading || !video}
        className="w-full bg-violet-600 hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium py-3 rounded-xl transition-colors text-sm"
      >
        {loading ? 'Cortando...' : 'Cortar Vídeo'}
      </button>
    </div>
  )
}
