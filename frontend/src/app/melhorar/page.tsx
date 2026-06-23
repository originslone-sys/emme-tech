'use client'

import { useState } from 'react'
import VideoDrop from '@/components/VideoDrop'

const API = process.env.NEXT_PUBLIC_API_URL || ''

export default function MelhorarPage() {
  const [video, setVideo] = useState<File | null>(null)
  const [scale, setScale] = useState(2)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')

  const submit = async () => {
    if (!video) return setError('Selecione um vídeo')
    setError(''); setStatus(''); setLoading(true)

    const form = new FormData()
    form.append('video', video)
    form.append('scale', String(scale))

    try {
      const res = await fetch(`${API}/api/editor/enhance`, { method: 'POST', body: form })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setStatus('Melhorando o vídeo... isso pode levar alguns minutos.')
      poll(data.job_id)
    } catch {
      setError('Erro ao enviar. Verifique a conexão e tente novamente.')
      setLoading(false)
    }
  }

  const poll = (id: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/editor/jobs/${id}`)
        const data = await res.json()
        if (data.status === 'COMPLETED') {
          clearInterval(interval)
          setLoading(false)
          setStatus('Vídeo melhorado! Acesse a Biblioteca para baixar.')
          setVideo(null)
        } else if (data.status === 'FAILED') {
          clearInterval(interval)
          setLoading(false)
          setError(data.error || 'Processamento falhou. Tente novamente.')
          setStatus('')
        }
      } catch { /* continua tentando */ }
    }, 3000)
  }

  return (
    <div className="max-w-xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Melhorar Qualidade</h1>
        <p className="text-white/40 mt-1">Aumente resolução, nitidez e reduza ruído com IA</p>
      </div>

      <div className="mb-6">
        <VideoDrop file={video} onChange={setVideo} />
      </div>

      <div className="mb-6">
        <label className="block text-sm font-medium text-white/60 mb-2">Nível de upscaling</label>
        <div className="flex gap-2">
          {[2, 4].map((s) => (
            <button
              key={s}
              onClick={() => setScale(s)}
              className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                scale === s ? 'bg-violet-600 text-white' : 'bg-white/5 text-white/50 hover:bg-white/10'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-red-400 text-sm mb-4">{error}</div>
      )}
      {loading && (
        <div className="bg-violet-500/10 border border-violet-500/20 rounded-lg px-4 py-3 text-violet-400 text-sm flex items-center gap-3 mb-4">
          <div className="w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin shrink-0" />
          {status}
        </div>
      )}
      {!loading && status && (
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg px-4 py-3 text-green-400 text-sm mb-4">{status}</div>
      )}

      <button
        onClick={submit}
        disabled={loading}
        className="w-full bg-violet-600 hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium py-3 rounded-xl transition-colors text-sm"
      >
        {loading ? 'Processando...' : 'Melhorar Vídeo'}
      </button>
    </div>
  )
}
