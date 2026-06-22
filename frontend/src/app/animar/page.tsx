'use client'

import { useState, useRef } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || ''

export default function AnimarPage() {
  const [image, setImage] = useState<File | null>(null)
  const [video, setVideo] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const imageInput = useRef<HTMLInputElement>(null)
  const videoInput = useRef<HTMLInputElement>(null)

  const submit = async () => {
    if (!image) return setError('Selecione uma imagem da modelo')
    if (!video) return setError('Selecione um vídeo de referência')

    setError('')
    setStatus('')
    setLoading(true)

    const form = new FormData()
    form.append('image', image)
    form.append('reference_video', video)

    try {
      const res = await fetch(`${API}/api/animate/`, { method: 'POST', body: form })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setStatus('Processando movimentos...')
      pollStatus(data.job_id)
    } catch {
      setError('Erro ao enviar. Verifique a conexão e tente novamente.')
      setLoading(false)
    }
  }

  const pollStatus = (id: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/animate/jobs/${id}`)
        const data = await res.json()

        if (data.status === 'COMPLETED') {
          clearInterval(interval)
          setLoading(false)
          setStatus('Vídeo gerado! Acesse a Biblioteca para baixar.')
          setImage(null)
          setVideo(null)
        } else if (data.status === 'FAILED') {
          clearInterval(interval)
          setLoading(false)
          setError(data.error || 'Processamento falhou. Tente novamente.')
          setStatus('')
        }
      } catch {
        // continua tentando
      }
    }, 3000)
  }

  return (
    <div className="max-w-xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Animar</h1>
        <p className="text-white/40 mt-1">Clone movimentos de um vídeo para sua imagem</p>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-white/60 mb-2">Imagem da modelo</label>
          <div
            className="border-2 border-dashed border-white/15 rounded-xl cursor-pointer hover:border-violet-500/40 transition-colors aspect-[3/4] flex flex-col items-center justify-center overflow-hidden"
            onClick={() => imageInput.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              const f = e.dataTransfer.files[0]
              if (f?.type.startsWith('image/')) setImage(f)
            }}
          >
            <input
              ref={imageInput}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && setImage(e.target.files[0])}
            />
            {image ? (
              <div className="relative w-full h-full group">
                <img
                  src={URL.createObjectURL(image)}
                  className="w-full h-full object-cover"
                  alt=""
                />
                <button
                  className="absolute top-2 right-2 bg-red-500 hover:bg-red-600 text-white rounded-full w-6 h-6 text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={(e) => { e.stopPropagation(); setImage(null) }}
                >
                  ×
                </button>
              </div>
            ) : (
              <>
                <div className="text-4xl text-white/15 mb-2">🖼️</div>
                <p className="text-white/30 text-xs text-center px-4">Clique ou arraste a imagem</p>
              </>
            )}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-white/60 mb-2">Vídeo de referência</label>
          <div
            className="border-2 border-dashed border-white/15 rounded-xl cursor-pointer hover:border-violet-500/40 transition-colors aspect-[3/4] flex flex-col items-center justify-center overflow-hidden"
            onClick={() => videoInput.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              const f = e.dataTransfer.files[0]
              if (f?.type.startsWith('video/')) setVideo(f)
            }}
          >
            <input
              ref={videoInput}
              type="file"
              accept="video/*"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && setVideo(e.target.files[0])}
            />
            {video ? (
              <div className="relative w-full h-full group">
                <video
                  src={URL.createObjectURL(video)}
                  className="w-full h-full object-cover"
                  muted
                  loop
                  autoPlay
                />
                <button
                  className="absolute top-2 right-2 bg-red-500 hover:bg-red-600 text-white rounded-full w-6 h-6 text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={(e) => { e.stopPropagation(); setVideo(null) }}
                >
                  ×
                </button>
              </div>
            ) : (
              <>
                <div className="text-4xl text-white/15 mb-2">🎥</div>
                <p className="text-white/30 text-xs text-center px-4">Clique ou arraste o vídeo</p>
              </>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-red-400 text-sm mb-4">
          {error}
        </div>
      )}

      {loading && (
        <div className="bg-violet-500/10 border border-violet-500/20 rounded-lg px-4 py-3 text-violet-400 text-sm flex items-center gap-3 mb-4">
          <div className="w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin shrink-0" />
          {status}
        </div>
      )}

      {!loading && status && (
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg px-4 py-3 text-green-400 text-sm mb-4">
          {status}
        </div>
      )}

      <button
        onClick={submit}
        disabled={loading}
        className="w-full bg-violet-600 hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium py-3 rounded-xl transition-colors text-sm"
      >
        {loading ? 'Processando...' : 'Gerar Vídeo'}
      </button>
    </div>
  )
}
