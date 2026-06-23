'use client'

import { useRef, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || ''

export default function JuntarPage() {
  const [videos, setVideos] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const input = useRef<HTMLInputElement>(null)

  const addFiles = (files: FileList | null) => {
    if (!files) return
    const vids = Array.from(files).filter((f) => f.type.startsWith('video/'))
    setVideos((prev) => [...prev, ...vids])
  }

  const move = (i: number, dir: -1 | 1) => {
    setVideos((prev) => {
      const next = [...prev]
      const j = i + dir
      if (j < 0 || j >= next.length) return prev
      ;[next[i], next[j]] = [next[j], next[i]]
      return next
    })
  }

  const remove = (i: number) => setVideos((prev) => prev.filter((_, idx) => idx !== i))

  const submit = async () => {
    if (videos.length < 2) return setError('Adicione pelo menos 2 vídeos')
    setError(''); setStatus(''); setLoading(true)

    const form = new FormData()
    videos.forEach((v) => form.append('videos', v))

    try {
      const res = await fetch(`${API}/api/editor/join`, { method: 'POST', body: form })
      if (!res.ok) throw new Error()
      await res.json()
      setStatus('Vídeos unidos! Acesse a Biblioteca para baixar.')
      setVideos([])
    } catch {
      setError('Erro ao juntar. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Juntar Vídeos</h1>
        <p className="text-white/40 mt-1">Monte a sequência e una tudo num só vídeo</p>
      </div>

      <div
        className="border-2 border-dashed border-white/15 rounded-xl cursor-pointer hover:border-violet-500/40 transition-colors py-8 flex flex-col items-center justify-center mb-6"
        onClick={() => input.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); addFiles(e.dataTransfer.files) }}
      >
        <input
          ref={input} type="file" accept="video/*" multiple className="hidden"
          onChange={(e) => { addFiles(e.target.files); e.target.value = '' }}
        />
        <div className="text-4xl text-white/15 mb-2">🎞️</div>
        <p className="text-white/30 text-sm">Clique ou arraste vídeos (pode adicionar vários)</p>
      </div>

      {videos.length > 0 && (
        <div className="space-y-2 mb-6">
          {videos.map((v, i) => (
            <div key={i} className="flex items-center gap-3 bg-[#111] border border-white/10 rounded-xl p-3">
              <span className="text-violet-400 font-mono text-sm w-6 text-center">{i + 1}</span>
              <video src={URL.createObjectURL(v)} className="w-24 aspect-video object-cover rounded-lg bg-black" muted />
              <span className="flex-1 text-white/60 text-sm truncate">{v.name}</span>
              <div className="flex gap-1">
                <button onClick={() => move(i, -1)} disabled={i === 0}
                  className="w-7 h-7 rounded-lg bg-white/5 hover:bg-white/10 disabled:opacity-20 text-white/60 text-sm">↑</button>
                <button onClick={() => move(i, 1)} disabled={i === videos.length - 1}
                  className="w-7 h-7 rounded-lg bg-white/5 hover:bg-white/10 disabled:opacity-20 text-white/60 text-sm">↓</button>
                <button onClick={() => remove(i)}
                  className="w-7 h-7 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 text-sm">×</button>
              </div>
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
          Unindo vídeos...
        </div>
      )}
      {!loading && status && (
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg px-4 py-3 text-green-400 text-sm mb-4">{status}</div>
      )}

      <button
        onClick={submit}
        disabled={loading || videos.length < 2}
        className="w-full bg-violet-600 hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium py-3 rounded-xl transition-colors text-sm"
      >
        {loading ? 'Processando...' : 'Juntar Vídeos'}
      </button>
    </div>
  )
}
