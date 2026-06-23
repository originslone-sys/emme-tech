'use client'

import { useState, useEffect, useCallback } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || ''

interface VideoItem {
  id: string
  filename: string
  label?: string
  created_at: string
}

const formatDate = (iso: string) =>
  new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })

export default function BibliotecaPage() {
  const [videos, setVideos] = useState<VideoItem[]>([])
  const [loading, setLoading] = useState(true)

  const fetchLibrary = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/library/`)
      const data = await res.json()
      setVideos((data.videos || []).reverse())
    } catch { /* falha silenciosa */ } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchLibrary() }, [fetchLibrary])

  const deleteVideo = async (id: string) => {
    if (!confirm('Excluir este vídeo permanentemente?')) return
    await fetch(`${API}/api/library/videos/${id}`, { method: 'DELETE' })
    fetchLibrary()
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Biblioteca</h1>
        <p className="text-white/40 mt-1">Seus vídeos processados</p>
      </div>

      {loading ? (
        <div className="text-white/30 text-center py-20 text-sm">Carregando...</div>
      ) : videos.length === 0 ? (
        <div className="text-white/20 text-center py-20 text-sm">Nenhum vídeo processado ainda</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {videos.map((vid) => (
            <div key={vid.id} className="bg-[#111] border border-white/10 rounded-xl overflow-hidden">
              <video
                src={`${API}/api/library/videos/${vid.id}/download`}
                className="w-full aspect-video object-cover bg-black"
                controls
              />
              <div className="p-3">
                {vid.label && <p className="text-white/70 text-sm font-medium truncate">{vid.label}</p>}
                <p className="text-white/30 text-xs mt-0.5">{formatDate(vid.created_at)}</p>
                <div className="flex gap-2 mt-3">
                  <a
                    href={`${API}/api/library/videos/${vid.id}/download`}
                    download
                    className="flex-1 bg-white/5 hover:bg-white/10 text-white/60 text-xs py-1.5 rounded-lg text-center transition-colors"
                  >
                    Baixar
                  </a>
                  <button
                    onClick={() => deleteVideo(vid.id)}
                    className="flex-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs py-1.5 rounded-lg transition-colors"
                  >
                    Excluir
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
