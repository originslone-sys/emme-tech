'use client'

import { useState } from 'react'
import Link from 'next/link'
import VideoDrop from '@/components/VideoDrop'

const API = process.env.NEXT_PUBLIC_API_URL || ''

export default function RepostarPage() {
  const [video, setVideo] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (!video) return setError('Selecione um vídeo')
    setError(''); setDone(false); setLoading(true)

    const form = new FormData()
    form.append('video', video)

    try {
      const res = await fetch(`${API}/api/editor/spin`, { method: 'POST', body: form })
      if (!res.ok) throw new Error()
      setDone(true)
      setVideo(null)
    } catch {
      setError('Erro ao processar. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Originalizar para Repostagem</h1>
        <p className="text-white/40 mt-1">
          Aplica transformações invisíveis que tornam o vídeo único para o algoritmo de cada plataforma
        </p>
      </div>

      <div className="bg-[#111] border border-white/10 rounded-xl p-4 mb-6">
        <p className="text-white/50 text-sm font-medium mb-2">O que é aplicado automaticamente:</p>
        <ul className="space-y-1.5">
          {[
            'Crop leve nas bordas (1–5%) — muda o frame sem cortar conteúdo visível',
            'Espelhamento horizontal aleatório',
            'Variação de velocidade ±3% — indetectável ao olho',
            'Ajuste sutil de brilho, contraste e saturação',
            'Logo micro invisível no canto — altera o hash do vídeo',
            'Re-encode em H.265 com parâmetros aleatórios',
          ].map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-white/40 text-xs">
              <span className="text-violet-400 shrink-0 mt-0.5">✓</span>
              {item}
            </li>
          ))}
        </ul>
      </div>

      <div className="mb-6">
        <VideoDrop file={video} onChange={(f) => { setVideo(f); setDone(false) }} />
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-red-400 text-sm mb-4">{error}</div>
      )}
      {loading && (
        <div className="bg-violet-500/10 border border-violet-500/20 rounded-lg px-4 py-3 text-violet-400 text-sm flex items-center gap-3 mb-4">
          <div className="w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin shrink-0" />
          Processando... (pode levar alguns minutos em H.265)
        </div>
      )}
      {done && (
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg px-4 py-3 text-green-400 text-sm mb-4">
          Vídeo pronto!{' '}
          <Link href="/biblioteca" className="underline">Ver na Biblioteca</Link>
        </div>
      )}

      <button
        onClick={submit}
        disabled={loading || !video}
        className="w-full bg-violet-600 hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium py-3 rounded-xl transition-colors text-sm"
      >
        {loading ? 'Processando...' : 'Originalizar Vídeo'}
      </button>
    </div>
  )
}
